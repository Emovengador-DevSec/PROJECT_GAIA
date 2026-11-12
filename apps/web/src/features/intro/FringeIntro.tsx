import { useEffect, useRef, useState } from "react";

/**
 * "Despertar de franjas": un shader WebGL dibuja franjas interferométricas que se expanden
 * desde el centro durante 1,2 s y se desvanecen. Es la única animación no solicitada de la app.
 * Con movimiento reducido no se muestra.
 */
const FRAG = `
precision mediump float;
uniform vec2 r; uniform float t;
vec3 ramp(float x){
  vec3 c[5]; c[0]=vec3(.95,.37,.36); c[1]=vec3(1.,.88,.4); c[2]=vec3(.44,.76,.70);
  c[3]=vec3(.14,.48,.63); c[4]=vec3(.56,.42,.75);
  float f=fract(x)*5.; int i=int(floor(f)); float k=fract(f);
  vec3 a=c[0], b=c[1];
  for(int j=0;j<5;j++){ if(j==i){ a=c[j]; b=c[j==4?0:j+1]; } }
  return mix(a,b,smoothstep(0.,1.,k));
}
void main(){
  vec2 p=(gl_FragCoord.xy-.5*r)/min(r.x,r.y);
  float d=length(p*vec2(1.,1.25));
  float front=t*1.4;
  float phase=d*9.-t*2.2+.15*sin(atan(p.y,p.x)*3.);
  float vis=smoothstep(front,front-.25,d)*(1.-smoothstep(.75,1.2,t));
  gl_FragColor=vec4(ramp(phase)*vis, vis*.9);
}`;
const VERT = "attribute vec2 a; void main(){ gl_Position=vec4(a,0.,1.); }";

export function FringeIntro({ onDone }: { onDone: () => void }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [gone, setGone] = useState(false);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const c = canvas.current;
    const gl = c?.getContext("webgl", { premultipliedAlpha: false });
    if (reduce || !c || !gl) { setGone(true); onDone(); return; }
    const sh = (type: number, src: string) => { const s = gl.createShader(type)!; gl.shaderSource(s, src); gl.compileShader(s); return s; };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VERT)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog); gl.useProgram(prog);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "a");
    gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    const uR = gl.getUniformLocation(prog, "r"), uT = gl.getUniformLocation(prog, "t");
    const t0 = performance.now(); let raf = 0;
    const frame = (now: number) => {
      const t = (now - t0) / 1000;
      c.width = c.clientWidth * devicePixelRatio; c.height = c.clientHeight * devicePixelRatio;
      gl.viewport(0, 0, c.width, c.height); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform2f(uR, c.width, c.height); gl.uniform1f(uT, t); gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (t < 1.2) raf = requestAnimationFrame(frame); else { setGone(true); onDone(); }
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [onDone]);

  if (gone) return null;
  return <canvas ref={canvas} aria-hidden style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 5 }} />;
}
