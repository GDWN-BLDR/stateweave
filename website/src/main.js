(function(){
let e=document.createElement(`link`).relList;
if(e&&e.supports&&e.supports(`modulepreload`))return;
for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);
new MutationObserver(e=>{
for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}
).observe(document,{
childList:!0,subtree:!0}
);
function t(e){
let t={
}
;
return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),e.crossOrigin===`use-credentials`?t.credentials=`include`:e.crossOrigin===`anonymous`?t.credentials=`omit`:t.credentials=`same-origin`,t}
function n(e){
if(e.ep)return;
e.ep=!0;
let n=t(e);
fetch(e.href,n)}
}
)();
function e(){
let e=document.getElementById(`terminal-text`);
if(!e)return;
let t=0;
function n(){
t<22&&(e.textContent+=`pip install stateweave`[t],t++,setTimeout(n,50+Math.random()*40))}
setTimeout(n,800)}
function t(){
let e=document.getElementById(`nav`),t=document.getElementById(`nav-toggle`),n=document.getElementById(`nav-links`),r=document.getElementById(`scroll-progress`),i=!1;
window.addEventListener(`scroll`,()=>{
i||=(requestAnimationFrame(()=>{
if(e.classList.toggle(`scrolled`,window.scrollY>16),r){
let e=window.scrollY,t=document.documentElement.scrollHeight-window.innerHeight,n=t>0?e/t*100:0;
r.style.width=n+`%`}
i=!1}
),!0)}
),t&&t.addEventListener(`click`,()=>{
n.classList.toggle(`open`)}
),n.querySelectorAll(`a[href^="#"]`).forEach(e=>{
e.addEventListener(`click`,()=>{
n.classList.remove(`open`)}
)}
)}
function n(){
let e=document.querySelectorAll(`.reveal`);
if(!e.length)return;
let t=new IntersectionObserver(e=>{
e.forEach(e=>{
e.isIntersecting&&(e.target.classList.add(`visible`),t.unobserve(e.target))}
)}
,{
threshold:.08,rootMargin:`0px 0px -40px 0px`}
);
e.forEach(e=>t.observe(e))}
function r(){
let e=document.querySelectorAll(`.demo-tab`),t=document.querySelectorAll(`.demo-panel`),n=document.getElementById(`demo-filename`),r={
export:`export.py`,import:`import.py`,encrypt:`migrate_encrypted.py`,diff:`diff_states.py`}
;
e.forEach(i=>{
i.addEventListener(`click`,()=>{
let a=i.dataset.tab;
e.forEach(e=>e.classList.remove(`active`)),t.forEach(e=>e.classList.remove(`active`)),i.classList.add(`active`),document.getElementById(`panel-${
a}
`).classList.add(`active`),n&&(n.textContent=r[a]||``)}
)}
)}
function i(){
document.querySelectorAll(`.copy-btn`).forEach(e=>{
e.addEventListener(`click`,async()=>{
let t=e.dataset.copy;
if(t)try{
await navigator.clipboard.writeText(t),e.classList.add(`copied`);
let n=e.querySelector(`svg`);
if(n){
let t=n.innerHTML;
n.innerHTML=`<polyline points="20 6 9 17 4 12" stroke="currentColor" stroke-width="2" fill="none"/>`,setTimeout(()=>{
n.innerHTML=t,e.classList.remove(`copied`)}
,1500)}
}
catch{
}
}
)}
)}
function a(){
document.querySelectorAll(`.faq-question`).forEach(e=>{
e.addEventListener(`click`,()=>{
let t=e.closest(`.faq-item`),n=t.querySelector(`.faq-answer`),r=t.classList.contains(`open`);
document.querySelectorAll(`.faq-item.open`).forEach(e=>{
e.classList.remove(`open`),e.querySelector(`.faq-answer`).style.maxHeight=`0`}
),r||(t.classList.add(`open`),n.style.maxHeight=n.scrollHeight+`px`)}
)}
)}
function o(){
document.querySelectorAll(`a[href^="#"]`).forEach(e=>{
e.addEventListener(`click`,t=>{
let n=e.getAttribute(`href`);
if(n===`#`)return;
let r=document.querySelector(n);
if(!r)return;
t.preventDefault();
let i=r.getBoundingClientRect().top+window.pageYOffset-76;
window.scrollTo({
top:i,behavior:`smooth`}
)}
)}
)}
async function s(){
try{
let e=await fetch(`https://api.github.com/repos/GDWN-BLDR/stateweave`);
if(!e.ok)return;
let t=await e.json(),n=document.getElementById(`star-count`);
n&&t.stargazers_count!=null&&(n.textContent=c(t.stargazers_count))}
catch{
}
}
function c(e){
return e>=1e3?(e/1e3).toFixed(1)+`k`:String(e)}
document.addEventListener(`DOMContentLoaded`,()=>{
e(),t(),n(),r(),i(),a(),o(),s()}
);
