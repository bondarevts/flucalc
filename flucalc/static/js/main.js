var c_sel = document.getElementById("c_selective");
var c_com = document.getElementById("c_complete");

var getRowsCount = function(area) {
    return area.value.split(/[\n\r]/).length;
}

var getAreaMaxHeight = function() {
    return window.innerHeight * 0.5 + 'px';
}

var updateTextareaHeight = function() {
    var result_height = Math.max(getRowsCount(c_sel), getRowsCount(c_com));
    c_sel.rows = c_com.rows = result_height + 1;
}

var setTextareaMaxHeight = function() {
    c_sel.style["maxHeight"] = c_com.style["maxHeight"] = getAreaMaxHeight();
}

window.onresize = setTextareaMaxHeight;

window.onload = function() {
    setTextareaMaxHeight();
    updateTextareaHeight();
}

c_sel.onscroll = function() {
    c_com.scrollTop = this.scrollTop;
}
c_com.onscroll = function() {
    c_sel.scrollTop = this.scrollTop;
}

c_sel.onkeyup = c_com.onkeyup = updateTextareaHeight
