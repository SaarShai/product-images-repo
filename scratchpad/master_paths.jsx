// master_paths.jsx — export artboard-1 path GEOMETRY (bezier points) to JSON.
// Read-only: does not modify the document. Run:
//   osascript -e 'tell application "Adobe Illustrator" to do javascript (POSIX file "<abs path>")'
// Output: <repo>/tasks/_templates/master_paths.json
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;

(function () {
  // open the MASTER TEMPLATE explicitly (active doc proved to be something else)
  var srcFile = new File("/Users/za/Documents/product images repo/tasks/_templates/drive-copies/screenery master template for images.ai");
  var doc = app.open(srcFile);
  var ab = doc.artboards[0].artboardRect; // [L, T, R, B] pts (y-up)
  var out = { artboard: [ab[0], ab[1], ab[2], ab[3]], paths: [] };

  function colorOf(it) {
    try {
      if (it.stroked && it.strokeColor.typename === "CMYKColor") {
        var c = it.strokeColor;
        return [Math.round(c.cyan), Math.round(c.magenta), Math.round(c.yellow), Math.round(c.black)];
      }
      if (it.stroked && it.strokeColor.typename === "RGBColor") {
        var r = it.strokeColor;
        return ["rgb", Math.round(r.red), Math.round(r.green), Math.round(r.blue)];
      }
    } catch (e) {}
    return null;
  }

  function inArtboard(it) {
    var b = it.geometricBounds; // [L, T, R, B]
    return !(b[2] < ab[0] || b[0] > ab[2] || b[1] < ab[3] || b[3] > ab[1]);
  }

  function dumpPath(p, parentName) {
    if (!inArtboard(p)) return;
    var pts = [];
    for (var i = 0; i < p.pathPoints.length; i++) {
      var pp = p.pathPoints[i];
      pts.push({
        a: [pp.anchor[0], pp.anchor[1]],
        l: [pp.leftDirection[0], pp.leftDirection[1]],
        r: [pp.rightDirection[0], pp.rightDirection[1]]
      });
    }
    var dash = [];
    try { dash = p.strokeDashes || []; } catch (e) {}
    out.paths.push({
      name: p.name || parentName || "",
      layer: (function () { try { return p.layer.name; } catch (e) { return ""; } })(),
      closed: p.closed,
      stroke_cmyk: colorOf(p),
      dashed: dash.length > 0,
      points: pts
    });
  }

  function walk(items, parentName) {
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      if (it.typename === "PathItem") dumpPath(it, parentName);
      else if (it.typename === "CompoundPathItem") {
        for (var j = 0; j < it.pathItems.length; j++) dumpPath(it.pathItems[j], it.name || parentName);
      } else if (it.typename === "GroupItem") walk(it.pageItems, it.name || parentName);
    }
  }

  for (var L = 0; L < doc.layers.length; L++) {
    var lay = doc.layers[L];
    if (!lay.visible) continue;
    walk(lay.pageItems, lay.name);
  }

  var f = new File("/Users/za/Documents/product images repo/tasks/_templates/master_paths.json");
  f.encoding = "UTF-8";
  f.open("w");
  // minimal JSON serializer (ExtendScript has no JSON on old versions)
  function ser(o) {
    if (o === null) return "null";
    if (typeof o === "number") return isFinite(o) ? String(Math.round(o * 100) / 100) : "null";
    if (typeof o === "boolean") return o ? "true" : "false";
    if (typeof o === "string") return '"' + o.replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
    if (o instanceof Array) {
      var a = [];
      for (var i = 0; i < o.length; i++) a.push(ser(o[i]));
      return "[" + a.join(",") + "]";
    }
    var k = [];
    for (var key in o) if (o.hasOwnProperty(key)) k.push('"' + key + '":' + ser(o[key]));
    return "{" + k.join(",") + "}";
  }
  f.write(ser(out));
  f.close();
  doc.close(SaveOptions.DONOTSAVECHANGES);   // read-only: never save
  "exported " + out.paths.length + " paths";
})();
