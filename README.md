# Google Photo Fixer
Tool for adding EXIF information to photos downloaded from Google Photos.

Original inspiration is from [rpanachi blog](at https://blog.rpanachi.com/how-to-takeout-from-google-photos-and-fix-metadata-exif-info), I've just used AI to convert his code to Python. It worked for me so I've decided to give it to the world.

## Dependencies
- exiftool

## Usage
1. Export your data using [https://takeout.google.com](https://takeout.google.com) tool. Download and unpack the file, in this example it's unpacked to directory `Takeout/Google Photos`.
2. Run this script: `./google-photos-fixer.py Takeout/Google\ Photos`.
3. Run:
`exiftool -r -d %s -tagsfromfile "%d/%F.supplemental-metadata.json"   "-GPSAltitude<GeoDataAltitude" "-GPSLatitude<GeoDataLatitude"   "-GPSLatitudeRef<GeoDataLatitude" "-GPSLongitude<GeoDataLongitude"   "-GPSLongitudeRef<GeoDataLongitude" "-Keywords<Tags" "-Subject<Tags"   "-Caption-Abstract<Description" "-ImageDescription<Description"   "-DateTimeOriginal<PhotoTakenTimeTimestamp"   -ext "*" -overwrite_original -progress --ext json -ifd0:all=   Takeout/Google\ Photos/`

