# Local PS3 package intake

**Reference:** *Vandal Hearts: Flames of Judgment*, EU PS3 title ID
`NPEB00148`. The user's package is expected to be about 605 MB,
but **no binary bytes have yet been verified by this repository**.

Only use copies of game data you lawfully possess and are permitted to analyze.
Keep the original and all license/activation material off GitHub.

## Split ZIP supplied as *.pkg.zip.001 and *.pkg.zip.002

First **inspect the filenames and confirm both volumes are present**.
There are multiple incompatible multipart ZIP conventions.

**Preferred method: read all parts as a virtual ZIP, without assembling,
extracting or uploading the package.** From the repository root run:

```sh
python3 -m tools.inspect_split_pkg \
  "Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.001" \
  "Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.002" \
  --expected-title-id NPEB00148 --sha256 --verify-crc --json > foj-pkg-report.json
```

The full-file hash and CRC require reading/decompressing the entire archive
but do not write the 605 MB payload anywhere. The JSON report contains no
extracted assets. Without these flags the inspector reads primarily the ZIP
index, PKG header and plaintext metadata; it does **not** verify archive
integrity. This only supports a raw byte-split regular ZIP, **not** a genuine
multi-disk/spanned ZIP.

**Fallback** if Python reports that the parts cannot form a regular ZIP:

For a ZIP that was **split into consecutive raw byte chunks**, on macOS/Linux:

```sh
cat "Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.001" \
    "Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.002" \
    > "foj-rejoined.zip"
unzip -t "foj-rejoined.zip"
unzip -l "foj-rejoined.zip"
```


This reconstruction changes **no source files**. Do not assume a successful
`cat` if the two volumes use true ZIP spanning rather than raw byte splitting.
If `unzip -t` fails, do **not** rename the pieces or delete originals.
Try a ZIP tool capable of reading multipart archives (for example, 7-Zip),
or identify how the volumes were produced.

If ZIP integrity passes, extract locally into a separate folder:

```sh
mkdir -p "foj-local"
unzip "foj-rejoined.zip" -d "foj-local"
find "foj-local" -type f -print
```


Use the actual extracted filename in the command below.

## Inspect *without* decryption

```sh
python3 tools/inspect_pkg.py "foj-local/ACTUAL_GAME_FILE.pkg" \
  --expected-title-id NPEB00148 --sha256 --json > "foj-pkg-report.json"
```


The script reads the **unencrypted container header** and bounded metadata.
It does **not** decrypt the contents, extract embedded resources, bypass DRM,
or prove that the package is complete, authorized, or playable.

- A content ID containing `NPEB00148` is useful evidence, not a cryptographic authentication.
- A declared file size matching the actual file size is a structural check,
  not proof of hash-level integrity.
- A SHA-256 identifies the exact bytes in your local copy; without a
  trusted reference hash it cannot independently authenticate the download.
- Some PKGs use formats or revisions not covered by this classic header parser.

**Share only the text/JSON report** at first. Do not publish the PKG,
EBOOT.BIN, RIF/RAP/EDAT licenses, cryptographic keys, or extracted assets.

## Format references

- https://www.psdevwiki.com/ps3/PKG_files
- https://github.com/hrydgard/ppsspp/blob/master/docs/pkg_notes.md
