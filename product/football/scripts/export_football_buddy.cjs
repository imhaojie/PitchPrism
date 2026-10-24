// Optional raster export for video bookends. Requires sharp; preserves the SVG source.
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const sharp = createRequire(path.join(__dirname, '../watch/package.json'))('sharp');
const source = path.join(__dirname, '../watch/football-buddy.js');
const output = process.argv[2];
if (!output) throw new Error('Pass the destination PNG path');
const svg = fs.readFileSync(source, 'utf8').match(/<svg[\s\S]*?<\/svg>/)[0]
  .replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ');
fs.mkdirSync(path.dirname(path.resolve(output)), {recursive:true});
sharp(Buffer.from(svg)).resize(320,340).png().toFile(output)
  .then(() => process.stdout.write('Football companion exported\n'));
