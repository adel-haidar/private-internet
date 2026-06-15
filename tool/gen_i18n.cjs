const fs = require('fs');
const dir = 'frontend/src/i18n/locales';
const codes = ['en','de','es','fr','ru','zh','ar'];
const out = {};
for (const c of codes) {
  let src = fs.readFileSync(`${dir}/${c}.ts`, 'utf8');
  src = src.replace(/export\s+const\s+\w+\s*=\s*/, '');     // drop the export prefix
  src = src.replace(/;\s*$/, '');                            // drop trailing semicolon
  out[c] = eval('(' + src + ')');                            // object literal -> object
}
let dart = '// GENERATED FILE — do not edit by hand.\n';
dart += '// Source: frontend/src/i18n/locales/*.ts via tool/gen_i18n.cjs.\n';
dart += '// Regenerate after changing the web locale files.\n\n';
dart += 'const Map<String, Map<String, dynamic>> kMessages = {\n';
for (const c of codes) {
  // $ would be Dart string interpolation; escape it. Unicode is kept as UTF-8.
  const json = JSON.stringify(out[c]).replace(/\$/g, '\\\$');
  dart += `  '${c}': ${json},\n`;
}
dart += '};\n';
fs.writeFileSync('mobile/lib/core/i18n/messages.g.dart', dart);
console.log('wrote messages.g.dart — locales:', codes.join(','), 'bytes:', dart.length);
