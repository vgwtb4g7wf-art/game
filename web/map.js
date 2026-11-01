function map(){
 let svg=`<svg viewBox="0 0 1000 760" role="img" aria-label="Карта Этериона: выберите город, чтобы посмотреть доступные действия"><defs>
 <pattern id="waves" width="45" height="30" patternUnits="userSpaceOnUse"><path d="M5 15q8-6 16 0t16 0" fill="none" stroke="#6b9d9e" stroke-width=".7" opacity=".18"/></pattern>
 <pattern id="forest" width="56" height="62" patternUnits="userSpaceOnUse"><path d="M28 9l-9 15h5l-7 10h22l-7-10h5z" fill="#284f3e" opacity=".4"/><path d="M28 34v8" stroke="#344b33"/></pattern>
 <pattern id="mountains" width="78" height="70" patternUnits="userSpaceOnUse"><path d="M6 61L37 12l31 49z" fill="#766b55" opacity=".5"/><path d="M37 12l-9 15 9-4 9 4z" fill="#e2d3af" opacity=".65"/></pattern>
 <pattern id="snow" width="80" height="65" patternUnits="userSpaceOnUse"><path d="M14 50L37 12l25 38z" fill="#729393" opacity=".25"/><path d="M37 12l-9 14 9-4 9 4z" fill="#e3e8d4" opacity=".8"/></pattern>
 <radialGradient id="water"><stop stop-color="#2b535a"/><stop offset="1" stop-color="#12313d"/></radialGradient>
<linearGradient id="dwarfColor" x2=".4" y2="1"><stop stop-color="#dbac72"/><stop offset="1" stop-color="#967248"/></linearGradient>
 <linearGradient id="snowColor" x2=".3" y2="1"><stop stop-color="#e1f1f3"/><stop offset="1" stop-color="#a5cbd9"/></linearGradient>
 <linearGradient id="forestColor" x2=".5" y2="1"><stop stop-color="#84b37b"/><stop offset="1" stop-color="#38694f"/></linearGradient>
 <linearGradient id="plainsColor" x2=".2" y2="1"><stop stop-color="#c5d18c"/><stop offset="1" stop-color="#89a45b"/></linearGradient>
 <linearGradient id="desertColor" x2=".4" y2="1"><stop stop-color="#f1d395"/><stop offset="1" stop-color="#d1a165"/></linearGradient>
 <linearGradient id="swampColor" x2=".5" y2="1"><stop stop-color="#8f9e79"/><stop offset="1" stop-color="#586a54"/></linearGradient>
 <linearGradient id="islandColor" x2=".5" y2="1"><stop stop-color="#b8badb"/><stop offset="1" stop-color="#7d92b0"/></linearGradient>
 <linearGradient id="ashColor" x2=".5" y2="1"><stop stop-color="#61545c"/><stop offset="1" stop-color="#302f3a"/></linearGradient>
 <pattern id="dunes" width="90" height="64" patternUnits="userSpaceOnUse"><path d="M0 44Q30 12 75 37M14 55Q40 30 90 46" fill="none" stroke="#a97538" stroke-width="1.2" opacity=".28"/><path d="M7 18q18-10 34 0" fill="none" stroke="#fff2bf" stroke-width="2" opacity=".5"/></pattern>
 <pattern id="plains" width="84" height="60" patternUnits="userSpaceOnUse"><path d="M0 40q24-14 53 0t30 0M10 47q26-12 60 0" stroke="#477744" fill="none" stroke-width="1" opacity=".3"/><path d="M24 22v-9m0 6l-4-3m4 6l4-3" stroke="#567444" opacity=".4"/></pattern>
 <pattern id="swamp" width="76" height="62" patternUnits="userSpaceOnUse"><ellipse cx="22" cy="38" rx="17" ry="6" fill="#608d92" opacity=".5"/><path d="M48 42v-17m0 9l-6-7m6 4l6-6m8 30v-12" fill="none" stroke="#3a5145" stroke-width="2" opacity=".6"/><path d="M4 11h20m-9 5h15" stroke="#a9b58d" opacity=".4"/></pattern>
 <pattern id="ash" width="78" height="70" patternUnits="userSpaceOnUse"><path d="M4 60L30 16l28 44z" fill="#222a31" opacity=".45"/><path d="M30 16l-5 15 10 8-5 21M60 8l-8 17 10 9" stroke="#db8054" fill="none" opacity=".6" stroke-width="1.4"/><circle cx="9" cy="12" r="1" fill="#dcb495" opacity=".6"/></pattern>
 <pattern id="islands" width="64" height="58" patternUnits="userSpaceOnUse"><path d="M20 32l10-17 10 17z" fill="#456b76" opacity=".35"/><path d="M12 42q18-9 37 0" stroke="#e1e6f1" fill="none" opacity=".5"/><circle cx="52" cy="10" r="1.5" fill="#dedff2"/></pattern>
 </defs><rect width="1000" height="760" fill="url(#water)"/><rect width="1000" height="760" fill="url(#waves)"/>`;
 // Общие границы строятся из одних и тех же вершин в обратном порядке.
 const border = {
  dwarfNorth:[[378,0],[397,38],[389,89],[360,131]],
  northForest:[[782,0],[783,52],[745,86],[706,129],[691,166]],
  northEmpire:[[691,166],[655,198],[604,228],[553,229],[507,205]],
  forestEmpire:[[691,166],[729,185],[751,223],[794,236],[815,269],[857,284],[883,327]],
  forestOrcs:[[883,327],[913,332],[948,355],[1000,326]],
  empireOrcs:[[883,327],[877,372],[850,408],[816,424],[811,461]],
  empireMountains:[[811,461],[777,452],[737,474],[693,470]],
  empireDesert:[[693,470],[669,450],[617,482],[584,464],[559,427]],
  desertMountains:[[693,470],[680,485],[666,525],[649,561],[653,596]],
  orcMountains:[[811,461],[824,488],[849,507],[862,535],[859,570],[881,599],[910,629],[936,616],[969,642],[1000,620]]
 };
 const rev=a=>[...a].reverse(), path=points=>'M'+points.map(p=>p.join(' ')).join('L')+'Z';
 const lands=[
 ['url(#dwarfColor)','mountains',path([[240,0],...border.dwarfNorth,[354,158],[306,193],[296,255],[260,302],[219,324],[177,301],[148,281],[142,234],[99,218],[112,187],[139,171],[146,129],[195,105],[229,67],[239,36]])],
 ['url(#snowColor)','snow',path([[378,0],...border.northForest,...border.northEmpire.slice(1),[487,175],[454,154],[426,155],[374,133],...rev(border.dwarfNorth)])],
 ['url(#forestColor)','forest',path([[782,0],[1000,0],[1000,326],...rev(border.forestOrcs).slice(1),...rev(border.forestEmpire).slice(1),...rev(border.northForest).slice(1)])],
 ['url(#plainsColor)','plains',path([...rev(border.northEmpire),...border.forestEmpire.slice(1),...border.empireOrcs.slice(1),...border.empireMountains.slice(1),...border.empireDesert.slice(1),[530,391],[547,348],[554,305],[531,273],[553,237]])],
 ['url(#desertColor)','dunes',path([[189,382],[219,392],[242,418],[271,412],[306,427],[336,438],[367,435],[402,452],[435,461],[462,483],[492,458],[530,452],[559,427],...rev(border.empireDesert).slice(1),...border.desertMountains.slice(1),[629,636],[600,650],[582,625],[542,619],[499,610],[469,611],[433,590],[405,583],[361,572],[322,570],[279,544],[250,521],[216,503],[195,476],[170,461],[178,427],[159,407]])],
 ['url(#swampColor)','swamp',path([...border.forestOrcs,[1000,620],...rev(border.orcMountains).slice(1),...rev(border.empireOrcs).slice(1)])],
 ['#777e77','mountains',path([...rev(border.empireMountains),...border.orcMountains.slice(1),[1000,760],[956,726],[920,706],[888,700],[847,681],[801,668],[757,638],[717,621],[685,605],[653,596],...rev(border.desertMountains).slice(1)])],
 ['url(#islandColor)','islands','M370 176L403 175 424 193 458 196 475 216 461 235 420 248 393 237 372 245 346 229 338 207z'],
 ['url(#islandColor)','islands','M301 307L326 300 348 312 370 298 392 313 415 320 437 347 421 368 389 371 364 398 330 389 314 372 283 367 270 345z'],
 ['url(#ashColor)','ash','M0 528L30 539 42 563 83 566 102 591 139 598 170 621 207 646 224 678 267 699 291 727 335 738 359 760 0 760z']
 ];
 for(const [color,pattern,path] of lands){svg+=`<path class="coast" fill="${color}" d="${path}"/>`;if(pattern)svg+=`<path d="${path}" fill="url(#${pattern})"/>`;}
 svg+=`<path d="M891 74Q846 139 887 190T909 326M608 62Q575 106 472 124" stroke="#538e9a" stroke-width="3" opacity=".7" fill="none"/>`;
 const labels=[['ДВАЛЛИНХОРГ',255,165],['КНЯЖЕСТВО БРЕННОР',567,135],['ТАЛЛАСА',868,190],['АЗАЛТИР',355,280],['ТРОТЕНФОРСКАЯ',699,338],['ИМПЕРИЯ',694,359],['АЛДОРИЯ',466,518],['АГРАМОР',924,520],['НАРХАЗ',116,722]];
 let countryLabels='';
 for(const [name,x,y] of labels)countryLabels+=`<text class="country ${name==='НАРХАЗ'?'ash-label':''}" x="${x}" y="${y}">${name}</text>`;
 svg+='<text class="sea" x="35" y="362" transform="rotate(-15 35 362)">Внешнее море</text><text class="sea" x="413" y="420">Внутреннее море</text><text class="sea" x="410" y="704">Великое море</text><g transform="translate(940 700)" fill="#bec3a5"><path d="M0-28L7-6 0 18-7-6z"/><path d="M-20-4L0-9 20-4 0 1z" opacity=".5"/><text x="-5" y="-34" font-family="Georgia">N</text></g>';
 for(const [a,b,kind] of catalog.routes){const [x,y]=coords[a],[xx,yy]=coords[b];const near=game&&[a,b].includes(game.hero.region);const war=game&&catalog.regions[a].country!==catalog.regions[b].country&&game.wars.some(pair=>pair.includes(catalog.regions[a].country)&&pair.includes(catalog.regions[b].country));svg+=`<path class="route-shadow" d="M${x} ${y}L${xx} ${yy}"/><path class="route ${kind==='море'?'sea-route':''} ${near?'near':''} ${war?'war':''}" d="M${x} ${y}L${xx} ${yy}"/>`;}
 svg+=countryLabels;
 for(const [name,[x,y]] of Object.entries(coords)){const r=catalog.regions[name],here=game&&game.hero.region===name;const neighbor=game&&game.neighbors.find(n=>n.name===name&&!n.error);const fill=r.blocked?'#7a4a40':here?'#b5e1be':neighbor?'#e8cf82':'#182c30';svg+=`<g class="node" tabindex="0" role="button" aria-label="${name}${here?', вы здесь':''}${r.blocked?', закрыт':''}" data-region="${name}" transform="translate(${x} ${y})"><title>${name} · ${r.country}</title><circle r="20" fill="transparent"/>`;if(selected===name)svg+='<circle r="18" fill="none" stroke="#e6c77e" stroke-width="1"/>';if(here)svg+='<circle r="23" fill="none" stroke="#a4d5b9" stroke-width="2" stroke-dasharray="3 4"/>';svg+=r.capital?`<path class="marker" d="M0-10L10 0 0 10-10 0Z" fill="${fill}" stroke="#e3d6b2" stroke-width="2"/>`:`<circle class="marker" r="6" fill="${fill}" stroke="#e3d6b2" stroke-width="2"/>`;svg+=`<text x="${x>850?-15:14}" y="${here?-16:5}" text-anchor="${x>850?'end':'start'}">${name}${r.blocked?' ⊗':''}</text>${here?`<text x="0" y="-29" text-anchor="middle" style="fill:#c3edcc;font:10px system-ui">${esc(game.avatar)} ВЫ ЗДЕСЬ</text>`:''}</g>`;}
 $('map').innerHTML=svg+'</svg>';
}
