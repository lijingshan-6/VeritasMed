const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),sharp=require('sharp');
const root=path.resolve(__dirname,'../reference');
(async()=>{const assets=[];
for(const name of fs.readdirSync(root).filter(n=>n.endsWith('.svg'))){
  const svg=path.join(root,name),png=svg.replace(/\.svg$/,'.png');
  await sharp(svg,{density:144}).png().toFile(png);
  for(const file of [svg,png]){const bytes=fs.readFileSync(file),m=await sharp(bytes).metadata();
    assets.push({file:path.basename(file),width:m.width,height:m.height,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),alpha:m.hasAlpha});}
}
fs.writeFileSync(path.join(root,'asset-manifest.json'),JSON.stringify({created:'2026-10-06',concept:'Unified serif in dark ink / teal with a sturdy citation V badge',assets},null,2)+'\n');
console.log(`Rendered and hashed ${assets.length} reference assets.`);
})().catch(e=>{console.error(e);process.exit(1)});
