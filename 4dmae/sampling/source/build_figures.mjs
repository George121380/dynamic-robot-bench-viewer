// Reuse the page's pure SVG renderer without launching a browser.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
const root=path.resolve(process.argv[2]);
const html=fs.readFileSync(path.join(root,'public/index.html'),'utf8');
const data=html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const code=html.split('<script>')[1].split('function toast(')[0];
const document={getElementById:()=>({textContent:data})};
for (const [kind,name] of [['seeds','seed-comparison'],['holdout','object-holdout'],['methods','sampling-methods']]) {
  const svg=vm.runInNewContext(code+`\nexportSvg('${kind}');`,{document});
  fs.writeFileSync(path.join(root,'public',name+'.svg'),svg);
  console.log(name+'.svg');
}
