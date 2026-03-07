$acad = "C:\Program Files\Autodesk\AutoCAD 2025\acad.exe"
$dwg = "C:\Users\josej\.openclaw\workspace\projects\solid_to_steel\Prueba_1.dwg"
$args = '/language "en-US" /product "ADVS" /p "<<ADVS>>" "' + $dwg + '"'

Start-Process -FilePath $acad -ArgumentList $args
