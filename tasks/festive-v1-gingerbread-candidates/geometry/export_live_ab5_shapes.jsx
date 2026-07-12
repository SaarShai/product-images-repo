function stringify(v) {
  if (v === null) return "null";
  if (v instanceof Array) {
    var a = [];
    for (var i = 0; i < v.length; i++) a.push(stringify(v[i]));
    return "[" + a.join(",") + "]";
  }
  if (typeof v == "object") {
    var parts = [];
    for (var k in v) {
      if (v.hasOwnProperty(k)) parts.push(stringify(k) + ":" + stringify(v[k]));
    }
    return "{" + parts.join(",") + "}";
  }
  if (typeof v == "string") {
    return '"' + v.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r/g, "\\r").replace(/\n/g, "\\n") + '"';
  }
  if (typeof v == "boolean") return v ? "true" : "false";
  return String(v);
}

function main() {
  if (!app.documents.length) return "no open document";
  var doc = app.activeDocument;
  var abIndex = 4; // user-facing artboard 5
  doc.artboards.setActiveArtboardIndex(abIndex);
  var ab = doc.artboards[abIndex].artboardRect;
  var abLeft = ab[0], abTop = ab[1], abRight = ab[2], abBottom = ab[3];
  var abW = abRight - abLeft;
  var abH = abTop - abBottom;

  var outDir = new Folder("/Users/za/Documents/product images repo/tasks/festive-v1-gingerbread-candidates/outputs/ab5-live");
  if (!outDir.exists) outDir.create();
  var png = new File(outDir.fsName + "/active-artboard-5-preview.png");
  var opts = new ExportOptionsPNG24();
  opts.artBoardClipping = true;
  opts.antiAliasing = true;
  opts.transparency = false;
  opts.horizontalScale = 30;
  opts.verticalScale = 30;
  doc.exportFile(png, ExportType.PNG24, opts);

  function intersects(b) {
    return !(b[2] < abLeft || b[0] > abRight || b[3] > abTop || b[1] < abBottom);
  }

  function pt(p) {
    return [p[0], p[1]];
  }

  var out = {
    doc: doc.name,
    artboard_index: 5,
    artboard_rect: [abLeft, abTop, abRight, abBottom],
    preview: png.fsName,
    paths: []
  };

  function addPath(p, itemPath) {
    if (!p.closed) return;
    if (p.hidden || p.locked) return;
    var b = p.geometricBounds;
    if (!intersects(b)) return;
    var area = Math.abs(p.area || 0);
    if (area < 800) return;
    var pts = [];
    for (var i = 0; i < p.pathPoints.length; i++) {
      var pp = p.pathPoints[i];
      pts.push({ anchor: pt(pp.anchor), left: pt(pp.leftDirection), right: pt(pp.rightDirection) });
    }
    var cx = (b[0] + b[2]) / 2;
    var cy = (b[1] + b[3]) / 2;
    out.paths.push({
      name: p.name || "",
      item_path: itemPath,
      layer: p.layer ? p.layer.name : "",
      bounds: [b[0], b[1], b[2], b[3]],
      center: [cx, cy],
      rel_center: [(cx - abLeft) / abW, (abTop - cy) / abH],
      width: Math.abs(b[2] - b[0]),
      height: Math.abs(b[1] - b[3]),
      area: area,
      filled: p.filled,
      stroked: p.stroked,
      points: pts
    });
  }

  function walk(item, itemPath) {
    if (item.hidden || item.locked) return;
    if (item.typename == "PathItem") addPath(item, itemPath);
    if (item.typename == "CompoundPathItem") {
      for (var c = 0; c < item.pathItems.length; c++) {
        walk(item.pathItems[c], itemPath + " > path[" + c + "]");
      }
    }
    if (item.pageItems) {
      for (var i = 0; i < item.pageItems.length; i++) {
        var child = item.pageItems[i];
        walk(child, itemPath + " > " + (child.name || child.typename + "[" + i + "]"));
      }
    }
  }

  for (var l = 0; l < doc.layers.length; l++) {
    var layer = doc.layers[l];
    if (layer.visible && !layer.locked) {
      for (var i = 0; i < layer.pageItems.length; i++) {
        var item = layer.pageItems[i];
        walk(item, layer.name + " > " + (item.name || item.typename + "[" + i + "]"));
      }
    }
  }

  var f = new File(outDir.fsName + "/active-artboard-5-shapes.json");
  f.encoding = "UTF-8";
  f.open("w");
  f.write(stringify(out));
  f.close();
  return "wrote " + out.paths.length + " paths; preview " + png.fsName;
}

main();
