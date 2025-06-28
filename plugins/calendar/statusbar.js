function updateTime() {
	var d = new Date().toISOString();
	document.getElementById("time_text").innerHTML = d.slice(0, 10)+" | "+d.slice(11, 19);
}
setInterval(updateTime, 1000);
