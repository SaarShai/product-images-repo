// Export tree cutout + all top-subpanel cutouts from active festive v1 doc, artboard 2.
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
  var doc = app.activeDocument;
  var ab = doc.artboards[1].artboardRect;
  var crop = { left: ab[0], top: 2000, right: ab[2], bottom: ab[3] };
  var out = {
    doc: doc.name,
    artboard_index: 2,
    artboard_rect: [ab[0], ab[1], ab[2], ab[3]],
    crop_rect: [crop.left, crop.top, crop.right, crop.bottom],
    paths: [],
    tree_hits: []
  };

  function intersects(b) {
    return !(b[2] < crop.left || b[0] > crop.right || b[3] > crop.top || b[1] < crop.bottom);
  }
  function pointArr(p) { return [p[0], p[1]]; }

  function keepPath(itemPath, p) {
    if (!p.closed) return false;
    var b = p.geometricBounds;
    if (!intersects(b)) return false;
    var area = Math.abs(p.area || 0);
    if (area < 2000) return false;
    if (itemPath.indexOf("outer contour") >= 0) return false;
    if (itemPath.indexOf("stabilizer 03") >= 0) return false;
    var low = (itemPath + " " + (p.name || "")).toLowerCase();
    if (low.indexOf("tree") >= 0) return true;
    if (itemPath.indexOf("top subpanel") >= 0 && itemPath.indexOf("cutout") >= 0) return true;
    if (itemPath.indexOf("bottom left subpanel") >= 0 && (itemPath.indexOf("cutout") >= 0 || itemPath.indexOf("PathItem") >= 0)) return true;
    if (itemPath.indexOf("bottom right subpanel") >= 0 && (itemPath.indexOf("cutout") >= 0 || itemPath.indexOf("PathItem") >= 0)) return true;
    return false;
  }

  function addPath(p, itemPath) {
    var low = (itemPath + " " + (p.name || "")).toLowerCase();
    if (low.indexOf("tree") >= 0) {
      out.tree_hits.push({
        name: p.name || "",
        item_path: itemPath,
        closed: !!p.closed,
        area: Math.abs(p.area || 0),
        bounds: [p.geometricBounds[0], p.geometricBounds[1], p.geometricBounds[2], p.geometricBounds[3]]
      });
    }
    if (!keepPath(itemPath, p)) return;
    var pts = [];
    for (var i = 0; i < p.pathPoints.length; i++) {
      var pp = p.pathPoints[i];
      pts.push({
        anchor: pointArr(pp.anchor),
        left: pointArr(pp.leftDirection),
        right: pointArr(pp.rightDirection)
      });
    }
    var b = p.geometricBounds;
    out.paths.push({
      name: p.name || "",
      item_path: itemPath,
      bounds: [b[0], b[1], b[2], b[3]],
      area: Math.abs(p.area || 0),
      points: pts
    });
  }

  function walk(item, itemPath) {
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

  try {
    var cut = doc.layers.getByName("cut");
    for (var i = 0; i < cut.pageItems.length; i++) {
      var item = cut.pageItems[i];
      walk(item, "cut > " + (item.name || item.typename + "[" + i + "]"));
    }
  } catch (e) {
    // fallback: walk all layers
    for (var li = 0; li < doc.layers.length; li++) {
      var layer = doc.layers[li];
      for (var j = 0; j < layer.pageItems.length; j++) {
        var it = layer.pageItems[j];
        walk(it, layer.name + " > " + (it.name || it.typename + "[" + j + "]"));
      }
    }
  }

  var f = new File("/Users/za/Documents/product images repo/tasks/festive-v1-gingerbread-candidates/geometry/ab2-cutouts-with-tree.json");
  f.encoding = "UTF-8";
  f.open("w");
  f.write(stringify(out));
  f.close();
  return "paths=" + out.paths.length + " tree_hits=" + out.tree_hits.length + " -> " + f.fsName;
}

main();
