using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Threading;
using Autodesk.AutoCAD.Runtime;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using AcApp = Autodesk.AutoCAD.ApplicationServices.Core.Application;

[assembly: ExtensionApplication(typeof(LilitASPlugin.PluginEntry))]

namespace LilitASPlugin
{
    public class PluginEntry : IExtensionApplication
    {
        private HttpListener? _listener;
        private Thread? _serverThread;
        private const int PORT = 18850;
        private static readonly string LOG_PATH = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "LilitASPlugin",
            "plugin.log");

        public void Initialize()
        {
            try
            {
                Log("Initialize() start");
                _listener = new HttpListener();
                _listener.Prefixes.Add($"http://localhost:{PORT}/");
                _listener.Prefixes.Add($"http://127.0.0.1:{PORT}/");
                Log($"Starting HttpListener on port {PORT}");
                _listener.Start();
                _serverThread = new Thread(ServeRequests) { IsBackground = true };
                _serverThread.Start();
                Log("HttpListener started successfully");
                AcApp.DocumentManager.MdiActiveDocument?
                    .Editor.WriteMessage($"\nLilitASPlugin activo en puerto {PORT}\n");
            }
            catch (System.Exception ex)
            {
                Log($"Initialize error: {ex}");
                AcApp.DocumentManager.MdiActiveDocument?
                    .Editor.WriteMessage($"\nLilitASPlugin error: {ex.Message}\n");
            }
        }

        public void Terminate()
        {
            try
            {
                Log("Terminate() called");
                _listener?.Stop();
            }
            catch (System.Exception ex)
            {
                Log($"Terminate error: {ex}");
            }
        }

        private void ServeRequests()
        {
            while (_listener?.IsListening == true)
            {
                try
                {
                    var ctx = _listener.GetContext();
                    ThreadPool.QueueUserWorkItem(_ => HandleRequest(ctx));
                }
                catch (System.Exception ex)
                {
                    Log($"ServeRequests loop stopped: {ex.Message}");
                    break;
                }
            }
        }

        private void HandleRequest(HttpListenerContext ctx)
        {
            string path = ctx.Request.Url?.AbsolutePath ?? "/";
            string method = ctx.Request.HttpMethod;
            string response = "{}";
            int status = 200;

            try
            {
                if (path == "/ping" && method == "GET")
                {
                    response = JsonSerializer.Serialize(new { status = "ok", plugin = "LilitASPlugin", port = PORT });
                }
                else if (path == "/elementos" && method == "GET")
                {
                    response = GetElementos(ctx.Request.QueryString["tipo"]);
                }
                else if (path.StartsWith("/elemento/") && method == "GET")
                {
                    string handle = path.Replace("/elemento/", "");
                    response = GetElementoByHandle(handle);
                }
                else
                {
                    status = 404;
                    response = JsonSerializer.Serialize(new { error = "ruta no encontrada" });
                }
            }
            catch (System.Exception ex)
            {
                status = 500;
                response = JsonSerializer.Serialize(new { error = ex.Message });
            }

            byte[] buffer = Encoding.UTF8.GetBytes(response);
            ctx.Response.StatusCode = status;
            ctx.Response.ContentType = "application/json; charset=utf-8";
            ctx.Response.ContentLength64 = buffer.Length;
            ctx.Response.OutputStream.Write(buffer, 0, buffer.Length);
            ctx.Response.OutputStream.Close();
        }

        private string GetElementos(string? tipoFiltro)
        {
            var elementos = new List<Dictionary<string, object>>();

            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return JsonSerializer.Serialize(new { error = "sin documento activo" });

            using (doc.LockDocument())
            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                var ms = (BlockTableRecord)tr.GetObject(
                    SymbolUtilityServices.GetBlockModelSpaceId(doc.Database),
                    OpenMode.ForRead);

                foreach (ObjectId id in ms)
                {
                    try
                    {
                        var obj = tr.GetObject(id, OpenMode.ForRead);
                        var props = new Dictionary<string, object>
                        {
                            ["handle"] = id.Handle.ToString(),
                            ["tipo"] = obj.GetType().Name,
                            ["clase"] = obj.GetRXClass().Name
                        };

                        if (obj is Entity ent)
                            props["capa"] = ent.Layer;

                        var objType = obj.GetType();
                        TryAdd(props, "peso_kg", objType, obj, "Weight");
                        TryAdd(props, "longitud_mm", objType, obj, "Length");
                        TryAdd(props, "perfil", objType, obj, "ProfSectionName");
                        TryAdd(props, "material", objType, obj, "Material");
                        TryAdd(props, "marca", objType, obj, "ItemNumber");
                        TryAdd(props, "descripcion", objType, obj, "Description");
                        TryAdd(props, "numero_pieza", objType, obj, "PartNumber");

                        if (tipoFiltro != null)
                        {
                            bool match =
                                props["tipo"].ToString()!.Contains(tipoFiltro, StringComparison.OrdinalIgnoreCase) ||
                                props["clase"].ToString()!.Contains(tipoFiltro, StringComparison.OrdinalIgnoreCase);
                            if (!match) continue;
                        }

                        elementos.Add(props);
                    }
                    catch { continue; }
                }

                tr.Commit();
            }

            return JsonSerializer.Serialize(new { total = elementos.Count, elementos });
        }

        private string GetElementoByHandle(string handle)
        {
            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return JsonSerializer.Serialize(new { error = "sin documento activo" });

            using (doc.LockDocument())
            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                try
                {
                    long handleLong = Convert.ToInt64(handle, 16);
                    var objHandle = new Handle(handleLong);
                    ObjectId id = doc.Database.GetObjectId(false, objHandle, 0);
                    var obj = tr.GetObject(id, OpenMode.ForRead);
                    var objType = obj.GetType();

                    var props = new Dictionary<string, object>
                    {
                        ["handle"] = handle,
                        ["tipo"] = objType.Name,
                        ["clase"] = obj.GetRXClass().Name
                    };

                    if (obj is Entity ent) props["capa"] = ent.Layer;

                    TryAdd(props, "peso_kg", objType, obj, "Weight");
                    TryAdd(props, "longitud_mm", objType, obj, "Length");
                    TryAdd(props, "perfil", objType, obj, "ProfSectionName");
                    TryAdd(props, "material", objType, obj, "Material");
                    TryAdd(props, "marca", objType, obj, "ItemNumber");
                    TryAdd(props, "descripcion", objType, obj, "Description");
                    TryAdd(props, "numero_pieza", objType, obj, "PartNumber");
                    TryAdd(props, "ancho_mm", objType, obj, "Width");
                    TryAdd(props, "alto_mm", objType, obj, "Height");
                    TryAdd(props, "espesor_mm", objType, obj, "Thickness");
                    TryAdd(props, "cantidad", objType, obj, "NumberOfElements");

                    tr.Commit();
                    return JsonSerializer.Serialize(props);
                }
                catch (System.Exception ex)
                {
                    return JsonSerializer.Serialize(new { error = ex.Message });
                }
            }
        }

        private static void Log(string message)
        {
            try
            {
                var dir = Path.GetDirectoryName(LOG_PATH);
                if (!string.IsNullOrWhiteSpace(dir)) Directory.CreateDirectory(dir);
                File.AppendAllText(LOG_PATH, $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}{Environment.NewLine}");
            }
            catch { }
        }

        private static void TryAdd(Dictionary<string, object> props,
            string key, Type type, object obj, string propName)
        {
            try
            {
                var prop = type.GetProperty(propName);
                if (prop != null)
                {
                    var val = prop.GetValue(obj);
                    if (val != null) props[key] = val;
                }
            }
            catch { }
        }
    }
}