import zipfile
import shutil
import os

shutil.copy2("dist/main.exe", "discordpet.exe")

zip_name = 'discordpet.zip'

with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('discordpet.exe')
    zf.write('assets/pet.png')

os.remove("discordpet.exe")

print(f'zipを作成しました。')