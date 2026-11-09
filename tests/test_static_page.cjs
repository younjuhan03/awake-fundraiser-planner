/* Execute the actual inline calculator without a browser; no external dependencies. */
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
const initial={units:'104',revenue:'375',buffer:'10',sell:'50',price:'3.5',cost:String(190/108),fixed:'0',preset:String(190/108)};
const elements={};
for(const [id,value] of Object.entries(initial)) elements[id]={value,validity:{valid:true},get valueAsNumber(){return Number(this.value)},addEventListener(){}};
elements.inputs={addEventListener(){},reset(){for(const [id,value] of Object.entries(initial))elements[id].value=value}};
elements.out={innerHTML:''};elements.reset={addEventListener(){}};
const context=vm.createContext({Intl,document:{getElementById:id=>elements[id]}});
const code=html.match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInContext(code,context);
function run(change={}){elements.inputs.reset();for(const [k,v]of Object.entries(change))elements[k].value=String(v);vm.runInContext('calculate()',context);return elements.out.innerHTML;}
let result=run();assert.match(result,/115 items/);assert.match(result,/-\$0\.10/);assert.match(result,/50\.3%/);assert.match(result,/\$191\.94/);
result=run({buffer:0});assert.match(result,/104 items/);assert.match(result,/No buffer selected/);assert.match(result,/\$192\.04/);
result=run({sell:0});assert.match(result,/-\$19\.35/);
result=run({sell:100});assert.match(result,/\+\$19\.15/);
result=run({units:0,revenue:0});assert.match(result,/0 items/);
result=run({units:0});assert.match(result,/Positive pre-order revenue requires/);
result=run({price:0,cost:4});assert.match(result,/Unreachable at a \$0/);
result=run({units:'Infinity'});assert.match(result,/Enter valid/);
result=run({cost:''});assert.match(result,/Enter valid/);
console.log('9 browser-calculator cases passed (DOM stub; visual layout not verified).');
