#target photoshop

/*
 * Bounded desktop-Photoshop scout for image14.
 *
 * Attempt 1 is Photoshop's bundled Remove Background sequence exactly:
 *   autoCutout(sampleAllLayers=false) -> make revealSelection user mask.
 * Attempt 2 starts from the same masked document, applies that mask, then runs
 * Remove White Matte. It does not create or change the segmentation mask.
 */

(function () {
    var sourcePath = "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png";
    var outputDir = "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/image14-research/photoshop-scout";
    var autoPath = outputDir + "/image14-photoshop-auto-mask.png";
    var decontPath = outputDir + "/image14-photoshop-auto-mask-remove-white-matte.png";

    function jsonString(value) {
        if (value === null) return "null";
        if (typeof value === "boolean" || typeof value === "number") return String(value);
        return '"' + String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r/g, "\\r").replace(/\n/g, "\\n") + '"';
    }

    function jsonObject(obj) {
        var fields = [];
        for (var key in obj) {
            if (obj.hasOwnProperty(key)) fields.push(jsonString(key) + ":" + jsonString(obj[key]));
        }
        return "{" + fields.join(",") + "}";
    }

    function exportPng24(doc, path) {
        app.activeDocument = doc;
        var options = new ExportOptionsSaveForWeb();
        options.format = SaveDocumentType.PNG;
        options.PNG8 = false;
        options.transparency = true;
        options.interlaced = false;
        options.includeProfile = true;
        doc.exportDocument(new File(path), ExportType.SAVEFORWEB, options);
    }

    function selectSubjectAndMakeMask() {
        var selectDescriptor = new ActionDescriptor();
        selectDescriptor.putBoolean(stringIDToTypeID("sampleAllLayers"), false);
        executeAction(stringIDToTypeID("autoCutout"), selectDescriptor, DialogModes.NO);

        var makeDescriptor = new ActionDescriptor();
        var maskReference = new ActionReference();
        makeDescriptor.putClass(charIDToTypeID("Nw  "), charIDToTypeID("Chnl"));
        maskReference.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
        makeDescriptor.putReference(charIDToTypeID("At  "), maskReference);
        makeDescriptor.putEnumerated(charIDToTypeID("Usng"), charIDToTypeID("UsrM"), charIDToTypeID("RvlS"));
        executeAction(charIDToTypeID("Mk  "), makeDescriptor, DialogModes.NO);
    }

    function applyCurrentLayerMask() {
        var selectDescriptor = new ActionDescriptor();
        var selectReference = new ActionReference();
        selectReference.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
        selectDescriptor.putReference(charIDToTypeID("null"), selectReference);
        selectDescriptor.putBoolean(charIDToTypeID("MkVs"), false);
        executeAction(charIDToTypeID("slct"), selectDescriptor, DialogModes.NO);

        var deleteDescriptor = new ActionDescriptor();
        var deleteReference = new ActionReference();
        deleteReference.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        deleteDescriptor.putReference(charIDToTypeID("null"), deleteReference);
        deleteDescriptor.putBoolean(charIDToTypeID("Aply"), true);
        executeAction(charIDToTypeID("Dlt "), deleteDescriptor, DialogModes.NO);
    }

    var originalDialogs = app.displayDialogs;
    var opened = [];
    var result = {
        status: "ERROR",
        photoshop_version: app.version,
        source: sourcePath,
        source_saved: false,
        source_width: null,
        source_height: null,
        automatic_attempts: 0,
        automatic_command: "autoCutout(sampleAllLayers=false) + make revealSelection user mask",
        select_subject_processing: "UNVERIFIED (descriptor does not expose Device/Cloud)",
        decontamination_attempts: 0,
        decontamination_command: "apply existing layer mask + removeWhiteMatte",
        automatic_output: autoPath,
        decontamination_output: decontPath,
        error: null
    };

    try {
        app.displayDialogs = DialogModes.NO;
        var sourceFile = new File(sourcePath);
        if (!sourceFile.exists) throw new Error("Source does not exist: " + sourcePath);

        var sourceDoc = app.open(sourceFile);
        opened.push(sourceDoc);
        result.source_width = Math.round(sourceDoc.width.as("px"));
        result.source_height = Math.round(sourceDoc.height.as("px"));

        var autoDoc = sourceDoc.duplicate("image14-photoshop-auto-mask", false);
        opened.push(autoDoc);
        sourceDoc.close(SaveOptions.DONOTSAVECHANGES);
        opened.shift();
        result.source_saved = false;

        app.activeDocument = autoDoc;
        result.automatic_attempts = 1;
        selectSubjectAndMakeMask();
        exportPng24(autoDoc, autoPath);

        var decontDoc = autoDoc.duplicate("image14-photoshop-auto-mask-remove-white-matte", false);
        opened.push(decontDoc);
        app.activeDocument = decontDoc;
        result.decontamination_attempts = 1;
        applyCurrentLayerMask();
        executeAction(stringIDToTypeID("removeWhiteMatte"), undefined, DialogModes.NO);
        exportPng24(decontDoc, decontPath);

        decontDoc.close(SaveOptions.DONOTSAVECHANGES);
        opened.pop();
        autoDoc.close(SaveOptions.DONOTSAVECHANGES);
        opened.pop();
        result.status = "OK";
    } catch (error) {
        result.error = error.message + " (line " + error.line + ")";
        for (var i = opened.length - 1; i >= 0; i--) {
            try { opened[i].close(SaveOptions.DONOTSAVECHANGES); } catch (ignored) {}
        }
    } finally {
        app.displayDialogs = originalDialogs;
    }

    return jsonObject(result);
}());
