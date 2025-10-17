#!/usr/bin/env python3
import os
import json
import shutil
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

class GooglePhotosFixer:
    METADATA_JSON = "supplemental-metadata.json"
    SUPPORTED_IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.mov', '.mp4', '.3gp', '.avi', '.mkv', '.webm']

    def __init__(self, takeout_dir: str):
        self.takeout_dir = takeout_dir
        self.fixes: List[str] = []
        self.errors: List[str] = []

    def reset(self):
        self.fixes = []
        self.errors = []

    def filename(self, fullpath_filename: str) -> str:
        return os.path.basename(fullpath_filename)

    def filename_without_ext(self, filename: str) -> str:
        return os.path.splitext(os.path.basename(filename))[0]

    def copy_file(self, origin: str, destination: str):
        shutil.copy2(origin, destination)
        self.fixes.append(f"{self.filename(origin)} copied to {self.filename(destination)}")

    def move_file(self, origin: str, destination: str):
        shutil.move(origin, destination)
        self.fixes.append(f"{self.filename(origin)} moved to {self.filename(destination)}")

    def delete_file(self, origin: str):
        os.remove(origin)

    def write_file(self, name: str, content: str):
        with open(name, 'w') as f:
            f.write(content)
        self.fixes.append(f"{self.filename(name)} written")

    def metadata_file_for(self, image_file: str) -> str:
        """Returns the default expected metadata filename"""
        return f"{image_file}.{self.METADATA_JSON}"

    def infer_time_from_image_file(self, image_file: str) -> Optional[datetime]:
        """Try to detect the timestamp from file name pattern"""
        filename = self.filename_without_ext(image_file)
        
        # Pattern: 20210529_155539
        match = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
        if match:
            groups = match.groups()
            if len(groups) == 6:
                try:
                    return datetime(*[int(x) for x in groups])
                except ValueError:
                    self.errors.append(f"Invalid date in filename: {image_file}")
                    return None

        # Pattern: CameraZOOM-20131224200623261
        match = re.search(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{3})', filename)
        if match:
            groups = match.groups()
            if len(groups) == 7:
                try:
                    return datetime(*[int(x) for x in groups[:6]], int(groups[6]) * 1000)
                except ValueError:
                    self.errors.append(f"Invalid date in filename: {image_file}")
                    return None

        # Pattern: DJI_20250308180700_0070_D
        match = re.search(r'_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})_', filename)
        if match:
            groups = match.groups()
            if len(groups) == 6:
                try:
                    return datetime(*[int(x) for x in groups])
                except ValueError:
                    self.errors.append(f"Invalid date in filename: {image_file}")
                    return None

        # Pattern: Photos from 2024/P01020304.jpg
        match = re.search(r'Photos from (\d{4})/', image_file)
        if match:
            groups = match.groups()
            if len(groups) == 1:
                return datetime(int(groups[0]), 1, 1)

        return None

    def generate_metadata_for_image_file(self, image_file: str):
        """Fallback to generate a metadata filename based on filename pattern"""
        metadata_filename = self.metadata_file_for(image_file)
        if os.path.exists(metadata_filename):
            return

        filename = self.filename_without_ext(image_file)
        time = self.infer_time_from_image_file(image_file)
        
        if time:
            json_content = {
                "title": self.filename(image_file),
                "description": f"Metadata inferred from {filename}",
                "imageViews": "1",
                "creationTime": {
                    "timestamp": str(int(time.timestamp())),
                    "formatted": str(time)
                },
                "photoTakenTime": {
                    "timestamp": str(int(time.timestamp())),
                    "formatted": str(time)
                }
            }
            self.write_file(metadata_filename, json.dumps(json_content, indent=2))
        else:
            self.errors.append(f"Unable to infer metadata for {image_file}")

    def fix_divergent_metadata_filename(self, json_file: str) -> str:
        """Normalize truncated json metadata filenames"""
        if not json_file.endswith(self.METADATA_JSON):
            parts = json_file.split('.')
            # Reconstruct with proper metadata filename
            fixed_json_file = re.sub(r'\.suppl\.json$', f'.{self.METADATA_JSON}', json_file)
            if fixed_json_file != json_file:
                self.move_file(json_file, fixed_json_file)
                json_file = fixed_json_file

        return json_file

    def fix_metadata_file_for_image(self, image_file: str) -> str:
        """Fix metadata files for various image naming patterns"""
        # Create metadata for "-editada" version
        if "-editada" in image_file:
            original_file = image_file.replace("-editada", "")
            original_meta = f"{original_file}.{self.METADATA_JSON}"

            if os.path.exists(original_meta):
                edited_meta = f"{image_file}.{self.METADATA_JSON}"
                self.copy_file(original_meta, edited_meta)

        # Fix metadata filenames for sequential images
        # Pattern: 20210529_155539(1).jpg
        filename_no_ext = self.filename_without_ext(image_file)
        match = re.search(r'(\(\d+\))$', filename_no_ext)
        
        if match:
            num = match.group(1)
            filename_without_num = self.filename(image_file).replace(num, "")
            # Remove extension from filename_without_num
            filename_without_num = filename_without_num.rsplit('.', 1)[0] + '.' + filename_without_num.rsplit('.', 1)[1]
            dir_path = os.path.dirname(image_file)

            wrong_json_file = os.path.join(dir_path, f"{filename_without_num}.supplemental-metadata{num}.json")
            fixed_json_file = os.path.join(dir_path, f"{self.filename(image_file)}.{self.METADATA_JSON}")
            
            if os.path.exists(wrong_json_file):
                if os.path.exists(fixed_json_file):
                    self.errors.append(f"Metadata file already exist: {fixed_json_file}")
                else:
                    self.move_file(wrong_json_file, fixed_json_file)
            else:
                self.errors.append(f"Metadata file: {wrong_json_file} not exist for image: {image_file}")

        return image_file

    def execute(self):
        self.reset()

        all_files = []
        for root, dirs, files in os.walk(self.takeout_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
        
        print(f"Total files found on {self.takeout_dir}: {len(all_files)}")

        years_files = [f for f in all_files if re.search(r'Photos from (\d+)$', os.path.dirname(f))]
        print(f"Total photos from YYYY dirs found: {len(years_files)}")

        image_files = [f for f in years_files if os.path.splitext(f)[1].lower() in self.SUPPORTED_IMAGE_EXT]
        print(f"Total supported photos formats found: {len(image_files)}")

        json_files = [f for f in years_files if os.path.splitext(f)[1].lower() == '.json']
        print(f"Total metadata files found: {len(json_files)}")

        json_files = [self.fix_divergent_metadata_filename(jf) for jf in json_files]

        for img in image_files:
            self.fix_metadata_file_for_image(img)
            self.generate_metadata_for_image_file(img)

        if len(self.errors) > 0:
            print(f"\nProcess finalized with {len(self.errors)} errors:")
            for index, error in enumerate(self.errors, 1):
                print(f"[{index}/{len(self.errors)}] {error}")

        if len(self.fixes) > 0:
            print(f"\nProcess finalized with {len(self.fixes)} fixes:")
            for index, fix in enumerate(self.fixes, 1):
                print(f"[{index}/{len(self.fixes)}] {fix}")

        not_found = [img for img in image_files if not os.path.exists(self.metadata_file_for(img))]

        if len(not_found) > 0:
            print(f"\nMetadata not found for {len(not_found)} files:")
            for index, file in enumerate(not_found, 1):
                print(f"[{index}/{len(not_found)}] {file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        raise ValueError("Usage: python fix_metadata.py path/to/takeout/dir/")
    
    takeout_dir = sys.argv[1]
    fixer = GooglePhotosFixer(takeout_dir)
    fixer.execute()
