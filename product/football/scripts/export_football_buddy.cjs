// Optional raster export for video bookends. Requires sharp; preserves the SVG source.
// `--mark <png>` exports the PitchPrism brand mark; a bare path exports the football companion.
const fs = require('node:fs');
const path = require('node:path');
const {createRequire} = require('node:module');
const sharp = createRequire(path.join(__dirname, '../watch/package.json'))('sharp');
const mark = process.argv[2] === '--mark';
const output = process.argv[mark ? 3 : 2];
if (!output) throw new Error('Pass the destination PNG path');
const svg = mark
  ? fs.readFileSync(path.join(__dirname, '../watch/mark.svg'), 'utf8')
  : fs.readFileSync(path.join(__dirname, '../watch/football-buddy.js'), 'utf8').match(/<svg[\s\S]*?<\/svg>/)[0]
      .replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ');
fs.mkdirSync(path.dirname(path.resolve(output)), {recursive:true});
const [width, height] = mark ? [512, 512] : [320, 340];
sharp(Buffer.from(svg), {density: mark ? 384 : 72}).resize(width, height).png().toFile(output)
  .then(() => process.stdout.write((mark ? 'Brand mark' : 'Football companion') + ' exported\n'));
