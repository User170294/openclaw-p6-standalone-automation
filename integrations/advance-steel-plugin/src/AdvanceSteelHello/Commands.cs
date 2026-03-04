using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

namespace AdvanceSteelHello
{
    public class Commands
    {
        [CommandMethod("SIMTEXX_HELLO")]
        public void SimtexxHello()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            Editor ed = doc.Editor;

            ed.WriteMessage("\n[SIMTEXX] Plugin cargado correctamente en Advance Steel.");
            ed.WriteMessage("\n[SIMTEXX] Siguiente paso: leer objetos del modelo y exportar propiedades.");
        }
    }
}
