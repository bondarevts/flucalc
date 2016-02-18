var v_tot = document.getElementById("v_total");
var c_sel = document.getElementById("c_selective");
var d_sel = document.getElementById("d_selective");
var v_sel = document.getElementById("v_selective");
var c_com = document.getElementById("c_complete");
var d_com = document.getElementById("d_complete");
var v_com = document.getElementById("v_complete");

var loadDataFromString = function(s) {
    var cFromString = function(s) {
        return s.split(",").join("\n");
    }

    var lines = s.split(/\r?\n/);

    v_tot.value = lines[0];
    c_sel.value = cFromString(lines[1]);
    d_sel.value = lines[2];
    v_sel.value = lines[3];
    c_com.value = cFromString(lines[4]);
    d_com.value = lines[5];
    v_com.value = lines[6];
}

var loadDataToString = function() {
    var cToString = function(c) {
        return c.split(/\s+/).join();
    }

    var result = [
        v_tot.value,
        cToString(c_sel.value),
        d_sel.value,
        v_sel.value,
        cToString(c_com.value),
        d_com.value,
        v_com.value
    ];
    return result.join("\n");
}

var file_load_button = document.getElementById("file-with-data");
file_load_button.addEventListener("change", function(event) {
    var file = file_load_button.files[0];

	var reader = new FileReader();
    reader.onload = function(event) {
        var contents = event.target.result;
        loadDataFromString(contents);
        updateTextareaHeight();
        document.getElementsByClassName("results")[0].style.display = "none";
    };

    reader.onerror = function(event) {
        console.error("File could not be read! Code " + event.target.error.code);
    };

    reader.readAsText(file);
}, false);

function download(filename, text) {
  var element = document.createElement('a');
  element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
  element.setAttribute('download', filename);

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);
}

var save_to_file_button = document.getElementById("save-to-file");

save_to_file_button.onclick = function() {
    download('flucalc-data.txt', loadDataToString());
}
