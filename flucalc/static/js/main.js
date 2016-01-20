var first = document.getElementById("c_selective");
var second = document.getElementById("c_complete");

var getRowsCount = function(area) {
    return area.value.split(/[\n\r]/).length;
}

var getAreaMaxHeight = function() {
    return window.innerHeight * 0.5 + 'px';
}

var updateTextareaHeight = function() {
    var result_height = Math.max(getRowsCount(first), getRowsCount(second));
    first.rows = second.rows = result_height + 1;
}

var setTextareaMaxHeight = function() {
    first.style["maxHeight"] = second.style["maxHeight"] = getAreaMaxHeight();
}

window.onresize = setTextareaMaxHeight;

window.onload = function() {
    setTextareaMaxHeight();
    updateTextareaHeight();
}

first.onscroll = function() {
    second.scrollTop = this.scrollTop;
}
second.onscroll = function() {
    first.scrollTop = this.scrollTop;
}

first.onkeyup = second.onkeyup = updateTextareaHeight
