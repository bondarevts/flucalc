var first = document.getElementById("c_selective");
var second = document.getElementById("c_complete");

var getRowsCount = function(area) {
    return area.value.split(/[\n\r]/).length;
}

var getAreaMaxHeight = function() {
    return window.innerHeight * 0.5 + 'px';
}

window.onload = window.onresize = function() {
    first.style["maxHeight"] = second.style["maxHeight"] = getAreaMaxHeight();
}

first.onscroll = function() {
    second.scrollTop = this.scrollTop;
}
second.onscroll = function() {
    first.scrollTop = this.scrollTop;
}

first.onkeyup = second.onkeyup = function() {
    var result_height = Math.max(getRowsCount(first), getRowsCount(second));
    first.rows = second.rows = result_height + 1;
}
