*ng_script
* Script to plot tesults of Spicebind MOS adder simulation.

load dump.raw
plot  v(a0) v(b0)+4 v(a1)+8 v(b1)+12 v(a2)+16 v(b2)+20 v(a3)+24 v(b3)+28 
* plot the outputs, use offset to plot on top of each other
plot  y0 v(y1)+4 v(y2)+8 v(y3)+12 v(13)+16
