using System;
using System.IO;
using System.Text;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
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
            ed.WriteMessage("\n[SIMTEXX] Comando nuevo: SIMTEXX_EXPORT_ATTRS");
        }

        [CommandMethod("SIMTEXX_EXPORT_ATTRS")]
        public void ExportSelectedAttributesToCsv()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            Editor ed = doc.Editor;
            Database db = doc.Database;

            try
            {
                PromptSelectionOptions pso = new PromptSelectionOptions
                {
                    MessageForAdding = "\nSelecciona objetos para exportar atributos: "
                };

                PromptSelectionResult selRes = ed.GetSelection(pso);
                if (selRes.Status != PromptStatus.OK)
                {
                    ed.WriteMessage("\n[SIMTEXX] No se seleccionaron objetos.");
                    return;
                }

                string docPath = string.IsNullOrWhiteSpace(doc.Name)
                    ? Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory)
                    : Path.GetDirectoryName(doc.Name) ?? Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);

                string outPath = Path.Combine(docPath, $"simtexx_attrs_{DateTime.Now:yyyyMMdd_HHmmss}.csv");

                using (Transaction tr = db.TransactionManager.StartTransaction())
                using (StreamWriter sw = new StreamWriter(outPath, false, new UTF8Encoding(true)))
                {
                    sw.WriteLine("handle,object_type,layer,color_index,linetype,lineweight,text,length,area,volume");

                    SelectionSet ss = selRes.Value;
                    foreach (SelectedObject so in ss)
                    {
                        if (so == null) continue;

                        DBObject dbo = tr.GetObject(so.ObjectId, OpenMode.ForRead, false);
                        if (!(dbo is Entity ent)) continue;

                        string handle = ent.Handle.ToString();
                        string objectType = ent.GetType().Name;
                        string layer = ent.Layer;
                        string colorIndex = ent.ColorIndex.ToString();
                        string linetype = ent.Linetype;
                        string lineweight = ent.LineWeight.ToString();
                        string text = "";
                        string length = "";
                        string area = "";
                        string volume = "";

                        if (ent is DBText dbText)
                            text = dbText.TextString;
                        else if (ent is MText mText)
                            text = mText.Contents;

                        if (ent is Curve curve)
                            length = curve.GetDistanceAtParameter(curve.EndParam).ToString("0.###");

                        if (ent is Region region)
                            area = region.Area.ToString("0.###");

                        if (ent is Solid3d solid)
                        {
                            try
                            {
                                Solid3dMassProperties mp = solid.MassProperties;
                                volume = mp.Volume.ToString("0.###");
                            }
                            catch
                            {
                                volume = "";
                            }
                        }

                        sw.WriteLine(string.Join(",",
                            Csv(handle),
                            Csv(objectType),
                            Csv(layer),
                            Csv(colorIndex),
                            Csv(linetype),
                            Csv(lineweight),
                            Csv(text),
                            Csv(length),
                            Csv(area),
                            Csv(volume)));
                    }

                    tr.Commit();
                }

                ed.WriteMessage($"\n[SIMTEXX] CSV exportado: {outPath}");
            }
            catch (System.Exception ex)
            {
                ed.WriteMessage($"\n[SIMTEXX] Error exportando atributos: {ex.Message}");
            }
        }

        private static string Csv(string value)
        {
            if (value == null) return "";
            if (value.Contains("\"") || value.Contains(",") || value.Contains("\n") || value.Contains("\r"))
                return "\"" + value.Replace("\"", "\"\"") + "\"";
            return value;
        }
    }
}
