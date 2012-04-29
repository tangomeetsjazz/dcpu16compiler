function start() {
  doLoop();
}

function doLoop() {
  for(x = 0; x <= 100; x = x + 1) {
    if(x == 1 || x == 3 || x == 5) {
      SCREEN[x] = 7364;
    }
  }
}

function end() {
  exit();
}
