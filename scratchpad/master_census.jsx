app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
(function () {
    function jstr(o) { // minimal JSON writer
        if (o === null || o === undefined) return "null";
        var t = typeof o;
        if (t === "number" || t === "boolean") return String(o);
        if (t === "string") return '"' + o.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n") + '"';
        if (o instanceof Array) { var a = []; for (var i = 0; i < o.length; i++) a.push(jstr(o[i])); return "[" + a.join(",") + "]"; }
        var k = []; for (var key in o) if (o.hasOwnProperty(key)) k.push(jstr(key) + ":" + jstr(o[key]));
        return "{" + k.join(",") + "}";
    }
    function emit(path, obj) { var f = new File(path); f.encoding = "UTF-8"; f.open("w"); f.write(jstr(obj)); f.close(); }
    function colorStr(c) {
        try {
            if (c.typename === "RGBColor") return "rgb(" + Math.round(c.red) + "," + Math.round(c.green) + "," + Math.round(c.blue) + ")";
            if (c.typename === "CMYKColor") return "cmyk(" + Math.round(c.cyan) + "," + Math.round(c.magenta) + "," + Math.round(c.yellow) + "," + Math.round(c.black) + ")";
            if (c.typename === "SpotColor") return "spot(" + c.spot.name + ")";
            if (c.typename === "GrayColor") return "gray(" + Math.round(c.gray) + ")";
            return c.typename;
        } catch (e) { return "err"; }
    }
    var OUT = "/tmp/master_census.json";
    try {
        var src = new File("/Users/za/Documents/product images repo/tasks/_templates/drive-copies/screenery master template for images.ai");
        var doc = app.open(src);
        var report = { ok: true, doc: doc.name, artboards: [], items: [] };
        for (var a = 0; a < doc.artboards.length; a++) {
            var ab = doc.artboards[a];
            report.artboards.push({ i: a, name: ab.name, rect: ab.artboardRect });
        }
        // artboard 01 = index 0 rect
        var r0 = doc.artboards[0].artboardRect; // [left, top, right, bottom]
        function onAB(b) { // visibleBounds [l,t,r,b]; overlap test with artboard 0
            return !(b[2] < r0[0] || b[0] > r0[2] || b[1] < r0[3] || b[3] > r0[1]);
        }
        var n = doc.pageItems.length;
        report.total_items = n;
        var cap = 0;
        for (var i = 0; i < n && cap < 400; i++) {
            var it = doc.pageItems[i];
            try {
                if (it.hidden) continue;
                var b = it.visibleBounds;
                if (!onAB(b)) continue;
                var rec = {
                    t: it.typename,
                    layer: (it.layer ? it.layer.name : ""),
                    name: it.name || "",
                    b: [Math.round(b[0]), Math.round(b[1]), Math.round(b[2]), Math.round(b[3])]
                };
                if (it.typename === "PathItem") {
                    rec.stroked = it.stroked;
                    if (it.stroked) {
                        rec.sc = colorStr(it.strokeColor);
                        rec.sw = Math.round(it.strokeWidth * 100) / 100;
                        rec.dash = (it.strokeDashes && it.strokeDashes.length > 0);
                    }
                    rec.filled = it.filled;
                    if (it.filled) rec.fc = colorStr(it.fillColor);
                    rec.closed = it.closed;
                    rec.pts = it.pathPoints ? it.pathPoints.length : 0;
                }
                if (it.typename === "GroupItem" || it.typename === "CompoundPathItem") {
                    rec.kids = it.pageItems ? it.pageItems.length : 0;
                }
                report.items.push(rec); cap++;
            } catch (e2) { }
        }
        // export artboard 0 as PNG
        doc.artboards.setActiveArtboardIndex(0);
        var w = r0[2] - r0[0];
        var scale = Math.min(100, (2400 / w) * 100);
        var opts = new ExportOptionsPNG24();
        opts.artBoardClipping = true;
        opts.horizontalScale = scale; opts.verticalScale = scale;
        opts.antiAliasing = true; opts.transparency = false;
        doc.exportFile(new File("/tmp/artboard01.png"), ExportType.PNG24, opts);
        report.export_scale = scale;
        doc.close(SaveOptions.DONOTSAVECHANGES);
        emit(OUT, report);
    } catch (e) {
        emit(OUT, { ok: false, err: e.message });
    }
})();
