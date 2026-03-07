using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using Microsoft.Win32.SafeHandles;
using Autodesk.AutoCAD.Runtime;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using AcApp = Autodesk.AutoCAD.ApplicationServices.Core.Application;

[assembly: ExtensionApplication(typeof(LilitASPlugin.PluginEntry))]

namespace LilitASPlugin
{
    public class PluginEntry : IExtensionApplication
    {
        private HttpListener? _listener;
        private Thread? _serverThread;
        private Thread? _pipeThread;
        private CancellationTokenSource? _pipeCts;

        private const int PORT = 18850;
        private const bool ENABLE_HTTP = false;
        private const string PIPE_NAME = "LilitASPluginPipe";

        private readonly ConcurrentQueue<UiWorkItem> _uiQueue = new();
        private int _pendingJobs = 0;

        private static readonly string LOG_PATH = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "LilitASPlugin",
            "plugin.log");

        private sealed class UiWorkItem
        {
            public required Func<string> Action { get; init; }
            public required ManualResetEventSlim Done { get; init; }
            public string ResultJson { get; set; } = JsonSerializer.Serialize(new { ok = false, error = "sin resultado" });
        }

        private sealed class PipeRequest
        {
            public string? method { get; set; }
            public string? path { get; set; }
            public Dictionary<string, string>? query { get; set; }
            public string? body { get; set; }
        }

        private sealed class PipeEnvelope
        {
            public int status { get; set; }
            public string body { get; set; } = "{}";
        }

        public void Initialize()
        {
            try
            {
                Log("Initialize() start");
                AcApp.Idle += OnApplicationIdle;

                _pipeCts = new CancellationTokenSource();
                _pipeThread = new Thread(() => ServePipeRequests(_pipeCts.Token))
                {
                    IsBackground = true,
                    Name = "LilitASPlugin.NamedPipe"
                };
                _pipeThread.Start();
                Log($"Named pipe server started: \\\\.\\pipe\\{PIPE_NAME}");

                if (ENABLE_HTTP)
                {
                    _listener = new HttpListener();
                    bool hasPrefix = false;

                    try
                    {
                        _listener.Prefixes.Add($"http://localhost:{PORT}/");
                        hasPrefix = true;
                        Log($"Prefix registered: http://localhost:{PORT}/");
                    }
                    catch (System.Exception ex)
                    {
                        Log($"Prefix registration failed (localhost): {ex.Message}");
                    }

                    try
                    {
                        _listener.Prefixes.Add($"http://127.0.0.1:{PORT}/");
                        hasPrefix = true;
                        Log($"Prefix registered: http://127.0.0.1:{PORT}/");
                    }
                    catch (System.Exception ex)
                    {
                        Log($"Prefix registration failed (127.0.0.1): {ex.Message}");
                    }

                    if (!hasPrefix)
                        throw new System.Exception($"No se pudo registrar ningún prefix HTTP para el puerto {PORT}");

                    Log($"Starting HttpListener on port {PORT}");
                    _listener.Start();

                    _serverThread = new Thread(ServeRequests) { IsBackground = true, Name = "LilitASPlugin.HttpListener" };
                    _serverThread.Start();

                    Log("HttpListener started successfully");
                }

                AcApp.DocumentManager.MdiActiveDocument?
                    .Editor.WriteMessage($"\nLilitASPlugin activo por named pipe (\\\\.\\pipe\\{PIPE_NAME})\n");
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
                AcApp.Idle -= OnApplicationIdle;
                _pipeCts?.Cancel();
                _listener?.Stop();
                _listener?.Close();
            }
            catch (System.Exception ex)
            {
                Log($"Terminate error: {ex}");
            }
        }

        private void OnApplicationIdle(object? sender, EventArgs e)
        {
            // Execute queued AutoCAD/Advance operations on UI thread
            while (_uiQueue.TryDequeue(out var item))
            {
                try
                {
                    item.ResultJson = item.Action();
                }
                catch (System.Exception ex)
                {
                    item.ResultJson = JsonSerializer.Serialize(new { ok = false, error = ex.Message });
                }
                finally
                {
                    Interlocked.Decrement(ref _pendingJobs);
                    item.Done.Set();
                }
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

        private void ServePipeRequests(CancellationToken token)
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    var security = new PipeSecurity();
                    security.AddAccessRule(new PipeAccessRule(
                        new SecurityIdentifier(WellKnownSidType.WorldSid, null),
                        PipeAccessRights.ReadWrite | PipeAccessRights.CreateNewInstance,
                        AccessControlType.Allow));

                    using var server = NamedPipeServerStreamAcl.Create(
                        PIPE_NAME,
                        PipeDirection.InOut,
                        NamedPipeServerStream.MaxAllowedServerInstances,
                        PipeTransmissionMode.Byte,
                        PipeOptions.Asynchronous,
                        4096,
                        4096,
                        security);

                    server.WaitForConnection();

                    using var reader = new StreamReader(server, Encoding.UTF8, false, 4096, leaveOpen: true);
                    using var writer = new StreamWriter(server, new UTF8Encoding(false), 4096, leaveOpen: true)
                    {
                        AutoFlush = true
                    };

                    var line = reader.ReadLine();
                    if (string.IsNullOrWhiteSpace(line))
                        continue;

                    var req = JsonSerializer.Deserialize<PipeRequest>(line);
                    var (status, body) = RouteRequest(
                        req?.path ?? "/",
                        req?.method ?? "GET",
                        key =>
                        {
                            if (key == "_body") return req?.body;
                            return req?.query != null && req.query.TryGetValue(key, out var val) ? val : null;
                        });

                    var envelope = new PipeEnvelope { status = status, body = body };
                    writer.WriteLine(JsonSerializer.Serialize(envelope));
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (System.Exception ex)
                {
                    Log($"Pipe server error: {ex.Message}");
                    Thread.Sleep(300);
                }
            }

            Log("Named pipe server stopped");
        }

        private void HandleRequest(HttpListenerContext ctx)
        {
            string? rawBody = null;
            try
            {
                using var sr = new StreamReader(ctx.Request.InputStream, ctx.Request.ContentEncoding ?? Encoding.UTF8, leaveOpen: true);
                rawBody = sr.ReadToEnd();
            }
            catch { }

            var (status, response) = RouteRequest(
                ctx.Request.Url?.AbsolutePath ?? "/",
                ctx.Request.HttpMethod,
                key =>
                {
                    if (key == "_body") return rawBody;
                    return ctx.Request.QueryString[key];
                });

            try
            {
                byte[] buffer = Encoding.UTF8.GetBytes(response);
                ctx.Response.StatusCode = status;
                ctx.Response.ContentType = "application/json; charset=utf-8";
                ctx.Response.ContentLength64 = buffer.Length;
                ctx.Response.OutputStream.Write(buffer, 0, buffer.Length);
            }
            finally
            {
                try { ctx.Response.OutputStream.Close(); } catch { }
            }
        }

        private (int status, string response) RouteRequest(string path, string method, Func<string, string?> query)
        {
            string response = "{}";
            int status = 200;

            try
            {
                if (path == "/ping" && method == "GET")
                {
                    response = JsonSerializer.Serialize(new { status = "ok", plugin = "LilitASPlugin", transport = "named-pipe", pipe = PIPE_NAME });
                }
                else if (path == "/status" && method == "GET")
                {
                    response = RunOnAcadThread(() => JsonSerializer.Serialize(GetStatus()));
                }
                else if (path == "/elementos" && method == "GET")
                {
                    string? tipo = query("tipo");
                    response = RunOnAcadThread(() => GetElementos(tipo));
                }
                else if (path.StartsWith("/elemento/") && method == "GET")
                {
                    string handle = path.Replace("/elemento/", "");
                    response = RunOnAcadThread(() => GetElementoByHandle(handle));
                }
                else if (path == "/bloques" && method == "GET")
                {
                    response = RunOnAcadThread(GetBloques);
                }
                else if (path == "/accion/explotar" && method == "POST")
                {
                    string? handle = query("handle");
                    response = RunOnAcadThread(() => ExplodeBlockByHandle(handle));
                }
                else if (path == "/accion/isolar" && method == "POST")
                {
                    string? handle = query("handle");
                    response = RunOnAcadThread(() => IsolateByHandle(handle));
                }
                else if (path == "/accion/mostrar_todo" && method == "POST")
                {
                    response = RunOnAcadThread(ShowAllObjects);
                }
                else if (path == "/accion/peso_bloque" && method == "GET")
                {
                    string? handle = query("handle");
                    string? densidad = query("densidad");
                    response = RunOnAcadThread(() => GetBlockWeight(handle, densidad));
                }
                else if (path == "/accion/area_handles" && method == "POST")
                {
                    string body = query("_body") ?? "{}";
                    response = RunOnAcadThread(() => GetAreaByHandlesFromJson(body));
                }
                else if (path == "/accion/ejecutar_comando" && method == "POST")
                {
                    string? cmd = query("cmd");
                    string? mapping = query("mapping");
                    string? handlesCsv = query("handles");
                    string? enters = query("enters");
                    response = RunOnAcadThread(() => ExecuteAcadCommand(cmd, mapping, handlesCsv, enters));
                }
                else if (path == "/accion/seleccionar" && method == "POST")
                {
                    string body = query("_body") ?? "{}";
                    response = RunOnAcadThread(() => SelectByHandlesFromJson(body));
                }
                else if (path == "/accion/convertir_visible_a_advance" && method == "POST")
                {
                    response = RunOnAcadThread(ConvertVisibleSolidsToAdvance);
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

            return (status, response);
        }

        private object GetStatus()
        {
            var doc = AcApp.DocumentManager.MdiActiveDocument;
            string? name = null;
            string? title = null;

            try { name = doc?.Name; } catch { }
            try { title = doc?.Window?.Text; } catch { }

            return new
            {
                status = "ok",
                plugin = "LilitASPlugin",
                transport = "named-pipe",
                pipe = PIPE_NAME,
                http_enabled = ENABLE_HTTP,
                port = ENABLE_HTTP ? PORT : (int?)null,
                pending_jobs = _pendingJobs,
                documento_activo = name,
                titulo_ventana = title,
                timestamp = DateTimeOffset.Now.ToString("O")
            };
        }

        private string RunOnAcadThread(Func<string> action, int timeoutMs = 15000)
        {
            using var done = new ManualResetEventSlim(false);
            var work = new UiWorkItem
            {
                Action = action,
                Done = done
            };

            _uiQueue.Enqueue(work);
            Interlocked.Increment(ref _pendingJobs);

            if (!done.Wait(timeoutMs))
            {
                return JsonSerializer.Serialize(new
                {
                    ok = false,
                    error = "timeout esperando ejecución en hilo AutoCAD",
                    timeout_ms = timeoutMs
                });
            }

            return work.ResultJson;
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
                        {
                            props["capa"] = ent.Layer;
                            props["visible"] = ent.Visible;
                        }
                        if (obj is BlockReference br)
                            props["nombre_bloque"] = br.Name;

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

                    if (obj is Entity ent)
                    {
                        props["capa"] = ent.Layer;
                        props["visible"] = ent.Visible;
                    }
                    if (obj is BlockReference br) props["nombre_bloque"] = br.Name;

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

        private string GetBloques()
        {
            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return JsonSerializer.Serialize(new { error = "sin documento activo" });

            using (doc.LockDocument())
            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                try
                {
                    var insertCounts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

                    var ms = (BlockTableRecord)tr.GetObject(
                        SymbolUtilityServices.GetBlockModelSpaceId(doc.Database),
                        OpenMode.ForRead);

                    foreach (ObjectId id in ms)
                    {
                        if (!id.ObjectClass.IsDerivedFrom(RXObject.GetClass(typeof(BlockReference)))) continue;
                        var br = tr.GetObject(id, OpenMode.ForRead) as BlockReference;
                        if (br == null) continue;

                        string name = br.Name ?? "(sin_nombre)";
                        if (!insertCounts.ContainsKey(name)) insertCounts[name] = 0;
                        insertCounts[name]++;
                    }

                    var bt = (BlockTable)tr.GetObject(doc.Database.BlockTableId, OpenMode.ForRead);
                    var bloques = new List<Dictionary<string, object>>();

                    foreach (ObjectId btrId in bt)
                    {
                        var btr = tr.GetObject(btrId, OpenMode.ForRead) as BlockTableRecord;
                        if (btr == null) continue;

                        string name = btr.Name ?? "(sin_nombre)";
                        int insertadas = insertCounts.ContainsKey(name) ? insertCounts[name] : 0;

                        bloques.Add(new Dictionary<string, object>
                        {
                            ["nombre"] = name,
                            ["insertadas"] = insertadas,
                            ["es_layout"] = btr.IsLayout,
                            ["es_anonimo"] = btr.IsAnonymous,
                            ["es_xref"] = btr.IsFromExternalReference
                        });
                    }

                    bloques.Sort((a, b) => string.Compare(
                        a["nombre"].ToString(),
                        b["nombre"].ToString(),
                        StringComparison.OrdinalIgnoreCase));

                    tr.Commit();
                    return JsonSerializer.Serialize(new { total = bloques.Count, bloques });
                }
                catch (System.Exception ex)
                {
                    return JsonSerializer.Serialize(new { error = ex.Message });
                }
            }
        }

        private string ExplodeBlockByHandle(string? handle)
        {
            if (string.IsNullOrWhiteSpace(handle))
                return JsonSerializer.Serialize(new { ok = false, error = "handle requerido" });

            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return JsonSerializer.Serialize(new { ok = false, error = "sin documento activo" });

            using (doc.LockDocument())
            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                try
                {
                    long handleLong = Convert.ToInt64(handle, 16);
                    var objHandle = new Handle(handleLong);
                    ObjectId id = doc.Database.GetObjectId(false, objHandle, 0);
                    var obj = tr.GetObject(id, OpenMode.ForWrite);

                    if (obj is not BlockReference br)
                        return JsonSerializer.Serialize(new { ok = false, error = "el handle no corresponde a BlockReference" });

                    string blockName = br.Name ?? "(sin_nombre)";
                    var ms = (BlockTableRecord)tr.GetObject(
                        SymbolUtilityServices.GetBlockModelSpaceId(doc.Database),
                        OpenMode.ForWrite);

                    var exploded = new DBObjectCollection();
                    br.Explode(exploded);

                    int created = 0;
                    foreach (DBObject dbo in exploded)
                    {
                        if (dbo is Entity ent)
                        {
                            ms.AppendEntity(ent);
                            tr.AddNewlyCreatedDBObject(ent, true);
                            created++;
                        }
                        else
                        {
                            dbo.Dispose();
                        }
                    }

                    br.Erase();
                    tr.Commit();

                    return JsonSerializer.Serialize(new
                    {
                        ok = true,
                        accion = "explotar",
                        handle,
                        bloque = blockName,
                        entidades_creadas = created
                    });
                }
                catch (System.Exception ex)
                {
                    return JsonSerializer.Serialize(new { ok = false, error = ex.Message, handle });
                }
            }
        }

        private string IsolateByHandle(string? handle)
        {
            if (string.IsNullOrWhiteSpace(handle))
                return JsonSerializer.Serialize(new { ok = false, error = "handle requerido" });

            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return JsonSerializer.Serialize(new { ok = false, error = "sin documento activo" });

            using (doc.LockDocument())
            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                try
                {
                    long handleLong = Convert.ToInt64(handle, 16);
                    var objHandle = new Handle(handleLong);
                    ObjectId targetId = doc.Database.GetObjectId(false, objHandle, 0);

                    var ms = (BlockTableRecord)tr.GetObject(
                        SymbolUtilityServices.GetBlockModelSpaceId(doc.Database),
                        OpenMode.ForRead);

                    int visible = 0, hidden = 0;
                    foreach (ObjectId id in ms)
                    {
                        var obj = tr.GetObject(id, OpenMode.ForWrite);
                        if (obj is not Entity ent) continue;

                        bool keepVisible = id == targetId;
                        ent.Visible = keepVisible;
                        if (keepVisible) visible++; else hidden++;
                    }

                    tr.Commit();
                    return JsonSerializer.Serialize(new { ok = true, accion = "isolar", handle, visible, hidden });
                }
                catch (System.Exception ex)
                {
                    return JsonSerializer.Serialize(new { ok = false, error = ex.Message, handle });
                }
            }
        }

        private string ShowAllObjects()
        {
            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return JsonSerializer.Serialize(new { ok = false, error = "sin documento activo" });

            using (doc.LockDocument())
            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                try
                {
                    var ms = (BlockTableRecord)tr.GetObject(
                        SymbolUtilityServices.GetBlockModelSpaceId(doc.Database),
                        OpenMode.ForRead);

                    int shown = 0;
                    foreach (ObjectId id in ms)
                    {
                        var obj = tr.GetObject(id, OpenMode.ForWrite);
                        if (obj is not Entity ent) continue;
                        ent.Visible = true;
                        shown++;
                    }

                    tr.Commit();
                    return JsonSerializer.Serialize(new { ok = true, accion = "mostrar_todo", shown });
                }
                catch (System.Exception ex)
                {
                    return JsonSerializer.Serialize(new { ok = false, error = ex.Message });
                }
            }
        }

        private string GetBlockWeight(string? handle, string? densidadText)
        {
            if (string.IsNullOrWhiteSpace(handle))
                return JsonSerializer.Serialize(new { ok = false, error = "handle requerido" });

            double densityKgM3 = 7850.0;
            if (!string.IsNullOrWhiteSpace(densidadText) && double.TryParse(densidadText, out var d) && d > 0)
                densityKgM3 = d;

            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return JsonSerializer.Serialize(new { ok = false, error = "sin documento activo" });

            using (doc.LockDocument())
            using (var tr = doc.Database.TransactionManager.StartTransaction())
            {
                try
                {
                    long handleLong = Convert.ToInt64(handle, 16);
                    var objHandle = new Handle(handleLong);
                    ObjectId id = doc.Database.GetObjectId(false, objHandle, 0);
                    var obj = tr.GetObject(id, OpenMode.ForRead);

                    if (obj is not BlockReference br)
                        return JsonSerializer.Serialize(new { ok = false, error = "el handle no corresponde a BlockReference" });

                    string nombre = br.Name ?? "(sin_nombre)";
                    var exploded = new DBObjectCollection();
                    br.Explode(exploded);

                    double totalMm3 = 0.0;
                    int solids = 0;
                    int others = 0;

                    foreach (DBObject dbo in exploded)
                    {
                        try
                        {
                            if (dbo is Solid3d s3d)
                            {
                                var mp = s3d.MassProperties;
                                totalMm3 += mp.Volume;
                                solids++;
                            }
                            else
                            {
                                others++;
                            }
                        }
                        catch
                        {
                            others++;
                        }
                        finally
                        {
                            dbo.Dispose();
                        }
                    }

                    // mm3 -> m3
                    double totalM3 = totalMm3 / 1_000_000_000.0;
                    double pesoKg = totalM3 * densityKgM3;

                    tr.Commit();
                    return JsonSerializer.Serialize(new
                    {
                        ok = true,
                        accion = "peso_bloque",
                        handle,
                        bloque = nombre,
                        densidad_kg_m3 = densityKgM3,
                        volumen_mm3 = totalMm3,
                        volumen_m3 = totalM3,
                        peso_kg = pesoKg,
                        solids,
                        others
                    });
                }
                catch (System.Exception ex)
                {
                    return JsonSerializer.Serialize(new { ok = false, error = ex.Message, handle });
                }
            }
        }

        private string GetAreaByHandlesFromJson(string? bodyJson)
        {
            // Pendiente: cálculo de área en API de AutoCAD 2025 (MassProperties no expone Area/SurfaceArea en esta build)
            // Se mantiene endpoint para compatibilidad de cliente.
            return JsonSerializer.Serialize(new
            {
                ok = false,
                error = "cálculo de área no disponible en esta versión del plugin",
                hint = "usar comando AREA/LIST en AutoCAD o implementar vía Brep API"
            });
        }

        private string SelectByHandlesFromJson(string? bodyJson)
        {
            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null)
                return JsonSerializer.Serialize(new { ok = false, error = "sin documento activo" });

            var handlesOk = new List<string>();
            var handlesError = new List<string>();
            var ids = new List<ObjectId>();

            try
            {
                if (string.IsNullOrWhiteSpace(bodyJson))
                    bodyJson = "{}";

                var root = JsonNode.Parse(bodyJson)?.AsObject();
                var arr = root?["handles"]?.AsArray();

                if (arr == null || arr.Count == 0)
                {
                    return JsonSerializer.Serialize(new
                    {
                        ok = false,
                        error = "handles requerido (array no vacío)"
                    });
                }

                using (doc.LockDocument())
                using (var tr = doc.Database.TransactionManager.StartTransaction())
                {
                    foreach (var item in arr)
                    {
                        string? h = item?.GetValue<string>()?.Trim();
                        if (string.IsNullOrWhiteSpace(h))
                        {
                            handlesError.Add("(vacío)");
                            continue;
                        }

                        try
                        {
                            long handleLong = Convert.ToInt64(h, 16);
                            var objHandle = new Handle(handleLong);
                            ObjectId id = doc.Database.GetObjectId(false, objHandle, 0);

                            var obj = tr.GetObject(id, OpenMode.ForRead);
                            if (obj is Entity)
                            {
                                ids.Add(id);
                                handlesOk.Add(h.ToUpperInvariant());
                            }
                            else
                            {
                                handlesError.Add(h.ToUpperInvariant());
                            }
                        }
                        catch
                        {
                            handlesError.Add(h.ToUpperInvariant());
                        }
                    }

                    tr.Commit();
                }

                doc.Editor.SetImpliedSelection(ids.ToArray());

                return JsonSerializer.Serialize(new
                {
                    ok = true,
                    total_seleccionados = ids.Count,
                    handles_ok = handlesOk,
                    handles_error = handlesError
                });
            }
            catch (System.Exception ex)
            {
                return JsonSerializer.Serialize(new
                {
                    ok = false,
                    error = ex.Message,
                    total_seleccionados = 0,
                    handles_ok = handlesOk,
                    handles_error = handlesError
                });
            }
        }

        private string ExecuteAcadCommand(string? cmd, string? mapping, string? handlesCsv, string? enters)
        {
            if (string.IsNullOrWhiteSpace(cmd))
                return JsonSerializer.Serialize(new { ok = false, error = "cmd requerido" });

            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return JsonSerializer.Serialize(new { ok = false, error = "sin documento activo" });

            try
            {
                // Selección atómica previa al comando (evita perder implied selection entre llamadas)
                var selected = new List<string>();
                var failed = new List<string>();
                if (!string.IsNullOrWhiteSpace(handlesCsv))
                {
                    var ids = new List<ObjectId>();
                    var parts = handlesCsv.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                    using (doc.LockDocument())
                    {
                        foreach (var p in parts)
                        {
                            try
                            {
                                long handleLong = Convert.ToInt64(p, 16);
                                var objHandle = new Handle(handleLong);
                                ObjectId id = doc.Database.GetObjectId(false, objHandle, 0);
                                ids.Add(id);
                                selected.Add(p.ToUpperInvariant());
                            }
                            catch
                            {
                                failed.Add(p.ToUpperInvariant());
                            }
                        }
                        doc.Editor.SetImpliedSelection(ids.ToArray());
                    }
                }

                string safe = cmd.Trim();

                // Automatización especial para Cocoon: responde al prompt del mapping CSV
                if (string.Equals(safe, "Cocoon", StringComparison.OrdinalIgnoreCase))
                {
                    string mapPath = string.IsNullOrWhiteSpace(mapping)
                        ? @"C:\Program Files\Autodesk\ApplicationPlugins\ComSpaceCocoonSuite2025.bundle\sectionlibraries\default_AUS_(mm).csv"
                        : mapping.Trim();

                    string macro = $"{safe}\n\"{mapPath}\"\n\n";
                    doc.SendStringToExecute(macro, true, false, false);

                    return JsonSerializer.Serialize(new
                    {
                        ok = true,
                        accion = "ejecutar_comando",
                        cmd = safe,
                        queued = true,
                        modo = "cocoon_auto_mapping",
                        mapping = mapPath,
                        selected,
                        failed
                    });
                }

                int extraEnters = 0;
                if (!string.IsNullOrWhiteSpace(enters)) int.TryParse(enters, out extraEnters);
                if (extraEnters < 0) extraEnters = 0;
                if (extraEnters > 10) extraEnters = 10;
                string macroCmd = safe + "\n" + new string('\n', extraEnters);

                doc.SendStringToExecute(macroCmd, true, false, false);
                return JsonSerializer.Serialize(new { ok = true, accion = "ejecutar_comando", cmd = safe, queued = true, selected, failed, enters = extraEnters });
            }
            catch (System.Exception ex)
            {
                return JsonSerializer.Serialize(new { ok = false, error = ex.Message, cmd, mapping, handlesCsv, enters });
            }
        }

        private string ConvertVisibleSolidsToAdvance()
        {
            var doc = AcApp.DocumentManager.MdiActiveDocument;
            if (doc == null) return JsonSerializer.Serialize(new { ok = false, error = "sin documento activo" });

            try
            {
                List<ObjectId> lineIds = new();
                using (doc.LockDocument())
                using (var tr = doc.Database.TransactionManager.StartTransaction())
                {
                    var ms = (BlockTableRecord)tr.GetObject(
                        SymbolUtilityServices.GetBlockModelSpaceId(doc.Database),
                        OpenMode.ForWrite);

                    foreach (ObjectId id in ms)
                    {
                        var obj = tr.GetObject(id, OpenMode.ForRead);
                        if (obj is not Solid3d s3d) continue;
                        if (obj is Entity ent && !ent.Visible) continue;

                        Extents3d ex;
                        try { ex = s3d.GeometricExtents; }
                        catch { continue; }

                        double dx = ex.MaxPoint.X - ex.MinPoint.X;
                        double dy = ex.MaxPoint.Y - ex.MinPoint.Y;
                        double dz = ex.MaxPoint.Z - ex.MinPoint.Z;

                        Autodesk.AutoCAD.Geometry.Point3d p1;
                        Autodesk.AutoCAD.Geometry.Point3d p2;

                        if (dx >= dy && dx >= dz)
                        {
                            double cy = (ex.MinPoint.Y + ex.MaxPoint.Y) / 2.0;
                            double cz = (ex.MinPoint.Z + ex.MaxPoint.Z) / 2.0;
                            p1 = new Autodesk.AutoCAD.Geometry.Point3d(ex.MinPoint.X, cy, cz);
                            p2 = new Autodesk.AutoCAD.Geometry.Point3d(ex.MaxPoint.X, cy, cz);
                        }
                        else if (dy >= dx && dy >= dz)
                        {
                            double cx = (ex.MinPoint.X + ex.MaxPoint.X) / 2.0;
                            double cz = (ex.MinPoint.Z + ex.MaxPoint.Z) / 2.0;
                            p1 = new Autodesk.AutoCAD.Geometry.Point3d(cx, ex.MinPoint.Y, cz);
                            p2 = new Autodesk.AutoCAD.Geometry.Point3d(cx, ex.MaxPoint.Y, cz);
                        }
                        else
                        {
                            double cx = (ex.MinPoint.X + ex.MaxPoint.X) / 2.0;
                            double cy = (ex.MinPoint.Y + ex.MaxPoint.Y) / 2.0;
                            p1 = new Autodesk.AutoCAD.Geometry.Point3d(cx, cy, ex.MinPoint.Z);
                            p2 = new Autodesk.AutoCAD.Geometry.Point3d(cx, cy, ex.MaxPoint.Z);
                        }

                        var ln = new Line(p1, p2) { Layer = "LILIT_AXES" };
                        ms.AppendEntity(ln);
                        tr.AddNewlyCreatedDBObject(ln, true);
                        lineIds.Add(ln.ObjectId);
                    }

                    tr.Commit();
                }

                if (lineIds.Count == 0)
                    return JsonSerializer.Serialize(new { ok = false, error = "no hay sólidos visibles para convertir" });

                doc.Editor.SetImpliedSelection(lineIds.ToArray());
                doc.SendStringToExecute("_.AstM4CommLine2Beam \n", true, false, false);

                return JsonSerializer.Serialize(new
                {
                    ok = true,
                    accion = "convertir_visible_a_advance",
                    solids_detectados = lineIds.Count,
                    metodo = "ejes_desde_bbox + AstM4CommLine2Beam",
                    queued = true
                });
            }
            catch (System.Exception ex)
            {
                return JsonSerializer.Serialize(new { ok = false, error = ex.Message });
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
