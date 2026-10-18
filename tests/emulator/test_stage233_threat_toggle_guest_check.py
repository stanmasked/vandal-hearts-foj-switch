"""Generated-only negative and positive screenshot cases for Stage233."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from tools.foj_stage233_threat_toggle_guest_check import verify_toggle
from tools.foj_stage231_threat_guest_check import BACKGROUND,HERO,ENEMY,SAFE,DANGER,SIZE

METER=(57,161,229)


def make(path:Path, *, visible=False, commands=1,
         bad_hero=False, bad_enemy=False, blank=False):
    im=Image.new("RGB",SIZE,(0,0,0) if blank else BACKGROUND)
    if not blank:
        d=ImageDraw.Draw(im)
        d.rectangle((580+(80 if bad_hero else 0),210,
                     609+(80 if bad_hero else 0),239),fill=HERO)
        d.rectangle((780+(80 if bad_enemy else 0),310,
                     809+(80 if bad_enemy else 0),339),fill=ENEMY)
        if commands:
            d.rectangle((412,104,411+commands,111),fill=METER)
        if visible:
            d.rectangle((651,224,655,226),fill=SAFE)
            d.rectangle((804,310,807,313),fill=DANGER)
            d.rectangle((810,310,813,313),fill=DANGER)
    im.save(path)


class Stage233ToggleTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.frames=tuple(Path(temp.name)/f"f{i}.png" for i in range(4))
        self.reset()

    def reset(self):
        make(self.frames[0],commands=0)
        make(self.frames[1],visible=True)
        make(self.frames[2])
        make(self.frames[3],visible=True)

    def test_valid_guest_sequence(self):
        self.assertTrue(verify_toggle(self.frames)["show_hide_show_proven"])

    def test_missing_selected_warning(self):
        make(self.frames[1])
        with self.assertRaises(ValueError):verify_toggle(self.frames)

    def test_hidden_frame_still_shows_warning(self):
        make(self.frames[2],visible=True)
        with self.assertRaises(ValueError):verify_toggle(self.frames)

    def test_restore_failed(self):
        make(self.frames[3])
        with self.assertRaises(ValueError):verify_toggle(self.frames)

    def test_initial_early_warning(self):
        make(self.frames[0],visible=True,commands=0)
        with self.assertRaises(ValueError):verify_toggle(self.frames)

    def test_toggle_accidentally_records_battle_input(self):
        make(self.frames[2],commands=2)
        with self.assertRaises(ValueError):verify_toggle(self.frames)

    def test_hero_changed(self):
        make(self.frames[2],bad_hero=True)
        with self.assertRaises(ValueError):verify_toggle(self.frames)

    def test_enemy_changed(self):
        make(self.frames[2],bad_enemy=True)
        with self.assertRaises(ValueError):verify_toggle(self.frames)

    def test_blank_guest(self):
        make(self.frames[2],blank=True)
        with self.assertRaises(ValueError):verify_toggle(self.frames)

    def test_wrong_resolution(self):
        Image.new("RGB",(960,600),BACKGROUND).save(self.frames[3])
        with self.assertRaises(ValueError):verify_toggle(self.frames)


if __name__=="__main__":
    unittest.main()
