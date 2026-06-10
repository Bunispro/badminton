# Player Profile Aesthetics Documentation

This document records the custom visual styles applied to player names based on their rank, as well as the country flag color mappings used for the moving border beams.

## Rank-Based Name Styles

The `<NameShine />` component in `web/frontend_new/app/player/[id]/page.tsx` applies different visual effects based on the player's current rank.

### 🏆 Rank 1: Ruby (Internal Glow & Low-Poly)
- **Color Scheme**: Dark Red to Bright Red (`#7f1d1d` → `#ef4444`).
- **Texture**: Low-poly geometric facets. An SVG pattern with varying opacities of red at `0.7` opacity.
- **Animation**: Internal Glow. A `drop-shadow` that breathes from a soft glow to a sharp one using Framer Motion.
- **Subtle Effect**: Diagonal Sweep. A high-contrast white glint line that wipes across the text at a 45-degree angle every 6 seconds.

### 🥈 Rank 2 & 3: Cobalt (Liquid Sapphire)
- **Color Scheme**: Vivid Cobalt to Electric Blue (`#1e3a8a` → `#3b82f6`).
- **Text Texture**: Caustics/Liquid. Moving radial gradients simulating light on water at `0.4` opacity.
- **Background Card Texture**: Drifting Waves at `0.03` opacity.
- **Animation**: Glinting Sparkle. Individual letters ping with a quick scale-up (`1.05`) and brightness flash.
- **Subtle Effect**: Outer Neon Bloom. A static, high-intensity blue outer glow (`textShadow: 0 0 15px #3b82f6`).

### 🥉 Rank 4 - 10: Emerald (Vertical Silk)
- **Color Scheme**: Mint-Green to Deep Forest (`#6EE7B7` → `#064E3B`).
- **Text Texture**: Vertical Silk Layers. Dense vertical lines simulating internal inclusions at `0.5` opacity.
- **Background Card Texture**: Drifting Diagonal Lines at `0.03` opacity.
- **Animation**: Parallax Pulse. Two layers of gradients moving in opposite directions on a 10s/15s loop creating a swirling depth effect.
- **Subtle Effect**: Chrome Stroke & Glass Edge (`textShadow: 0 1px 1px rgba(255,255,255,0.3)`).

### 🛠️ Rank 11 - 20: Matte Gold (Anodized)
- **Color Scheme**: Warm Gold to Burnt Amber (`#FCD34D` → `#B45309`).
- **Texture**: Anodic Micro-Pitting. Fine grain/sandblasted texture at `0.15` opacity.
- **Animation**: Data Pulse. A subtle brightness breathing effect from matte to satin.
- **Subtle Effect**: Sharp Perimeter Stroke. A tiny `0.5px` white-gold stroke (`#FEF3C7`) around the text.

### 🪵 Rank 21 - 50: Precision Silver (Machined)
- **Color Scheme**: Pale Steel to Muted Slate (`#CBD5E1` → `#64748B`). Balanced contrast for texture visibility.
- **Texture**: Precision Machined Knurl. 30-degree diagonal grid with thin dark lines at `0.1` and `0.4` opacity.
- **Animation**: The Surface Glaze. A moving gradient mask that sharpens the texture as it passes.
- **Subtle Effect**: Hard Edge Definition. A `0.75px` bright silver stroke (`#E2E8F0`) for a cut-metal edge.

### 🟫 Rank 51 - 100: Ground Bronze (Industrial)
- **Color Scheme**: Pale Copper to Deep Bronze (`#d97706` → `#92400e`). Darker amber tones at the top.
- **Texture**: Industrial Grind. Heavy 60-degree diagonal scratches catching light.
- **Animation**: The Static Flicker. A low-frequency opacity jitter (dropping to 0.4) once every 5 seconds.
- **Subtle Effect**: Copper Rim. A `1px` soft orange-red outer glow (`textShadow: 0 0 2px rgba(234, 88, 12, 0.3)`) for a heat silhouette.

---

## Country Flag Color Mappings

The `getBeamColors` function maps country codes to their flag colors for the `BorderBeam` component. If a flag has more than 3 colors, the 3 most prominent colors are used.

| Country Code | Country | Color 1 (From) | Color 2 (Middle) | Color 3 (To) |
| :--- | :--- | :--- | :--- | :--- |
| **DK** | Denmark | `#ef4444` (Red) | - | `#ffffff` (White) |
| **CN** | China | `#dc2626` (Red) | - | `#facc15` (Yellow) |
| **JP** | Japan | `#dc2626` (Red) | - | `#ffffff` (White) |
| **MY** | Malaysia | `#1d4ed8` (Blue) | `#facc15` (Yellow) | `#dc2626` (Red) |
| **ID** | Indonesia | `#dc2626` (Red) | - | `#ffffff` (White) |
| **KR** | South Korea | `#ffffff` (White) | `#dc2626` (Red) | `#1d4ed8` (Blue) |
| **TH** | Thailand | `#e60000` (Red) | `#ffffff` (White) | `#052c65` (Blue) |
| **IND** | India | `#ea580c` (Orange)| `#ffffff` (White) | `#16a34a` (Green) |
| **FR** | France | `#052c65` (Blue) | `#ffffff` (White) | `#e60000` (Red) |
| **SG** | Singapore | `#ef3340` (Red) | - | `#ffffff` (White) |
| **TPE** | Chinese Taipei | `#000095` (Blue) | `#ffffff` (White) | `#fe0000` (Red) |
| **HK / HKG** | Hong Kong | `#de2110` (Red) | - | `#ffffff` (White) |
| **VN** | Vietnam | `#da251d` (Red) | - | `#ffff00` (Yellow) |
| **FI** | Finland | `#ffffff` (White) | - | `#002f6c` (Blue) |
| **ENG** | England | `#ffffff` (White) | - | `#ce1126` (Red) |
| **IE** | Ireland | `#169b62` (Green) | `#ffffff` (White) | `#ff883e` (Orange) |
| **DE** | Germany | `#000000` (Black) | `#dd0000` (Red) | `#ffce00` (Yellow) |
| **NL** | Netherlands | `#ae1c28` (Red) | `#ffffff` (White) | `#21468b` (Blue) |
| **CA** | Canada | `#ff0000` (Red) | - | `#ffffff` (White) |
| **PL** | Poland | `#ffffff` (White) | - | `#dc143c` (Red) |
| **PH** | Philippines | `#0038a8` (Blue) | `#ffffff` (White) | `#ce1126` (Red) |
| **US / USA** | USA | `#002868` (Blue) | `#ffffff` (White) | `#bf0a30` (Red) |
| **MX** | Mexico | `#006847` (Green) | `#ffffff` (White) | `#ce1126` (Red) |
| **BR** | Brazil | `#009739` (Green) | `#fed141` (Yellow) | `#012169` (Blue) |
| **AR** | Argentina | `#75aadb` (Sky Blue)| `#ffffff` (White) | `#f6b40e` (Yellow) |
| **ZA** | South Africa | `#007a4d` (Green) | `#ffb612` (Gold) | `#000000` (Black) |
| **IT** | Italy | `#008c45` (Green) | `#ffffff` (White) | `#cd212a` (Red) |
| **SE** | Sweden | `#006aa7` (Blue) | - | `#fecc00` (Yellow) |
| **NO** | Norway | `#ba0c2f` (Red) | `#ffffff` (White) | `#00205b` (Blue) |
| **RU** | Russia | `#ffffff` (White) | `#0039a6` (Blue) | `#d52b1e` (Red) |
| **PK** | Pakistan | `#00401a` (Green) | - | `#ffffff` (White) |
| **AF** | Afghanistan | `#000000` (Black) | `#bf0000` (Red) | `#009900` (Green) |
| **AL** | Albania | `#e41e20` (Red) | - | `#000000` (Black) |
| **DZ** | Algeria | `#006633` (Green) | `#ffffff` (White) | `#d21034` (Red) |
| **AD** | Andorra | `#0018a8` (Blue) | `#fed141` (Yellow) | `#ea3323` (Red) |
| **AO** | Angola | `#da121a` (Red) | `#000000` (Black) | `#f9d616` (Yellow) |
| **AG** | Antigua and Barbuda | `#000000` (Black) | `#0072c6` (Blue) | `#ef3340` (Red) |
| **AM** | Armenia | `#ff0000` (Red) | `#0033a0` (Blue) | `#f2a800` (Orange) |
| **AU** | Australia | `#002b7f` (Blue) | `#ffffff` (White) | `#e8112d` (Red) |
| **AT** | Austria | `#ef3340` (Red) | - | `#ffffff` (White) |
| **AZ** | Azerbaijan | `#0097c3` (Blue) | `#e01021` (Red) | `#3f9c35` (Green) |
| **BS** | Bahamas | `#00a9ce` (Aquamarine)| `#f9d616` (Yellow) | `#000000` (Black) |
| **BH** | Bahrain | `#ce1126` (Red) | - | `#ffffff` (White) |
| **BD** | Bangladesh | `#006a4e` (Green) | - | `#f42a41` (Red) |
| **BB** | Barbados | `#00267f` (Blue) | `#ffb81c` (Gold) | `#000000` (Black) |
| **BY** | Belarus | `#c8102e` (Red) | - | `#489a5e` (Green) |
| **BE** | Belgium | `#000000` (Black) | `#f9d616` (Yellow) | `#ef3340` (Red) |
| **BZ** | Belize | `#003f87` (Blue) | `#ce1126` (Red) | `#ffffff` (White) |
| **BJ** | Benin | `#008751` (Green) | `#fcd116` (Yellow) | `#e8112d` (Red) |
| **BT** | Bhutan | `#ffcc00` (Yellow) | - | `#ff4d00` (Orange) |
| **BO** | Bolivia | `#da291c` (Red) | `#f4e400` (Yellow) | `#007a33` (Green) |
| **BA** | Bosnia and Herzegovina | `#002f6c` (Blue) | `#fecb00` (Yellow) | `#ffffff` (White) |
| **BW** | Botswana | `#75aadb` (Light Blue)| `#000000` (Black) | `#ffffff` (White) |
| **BN** | Brunei | `#f7e017` (Yellow) | `#000000` (Black) | `#ffffff` (White) |
| **BG** | Bulgaria | `#ffffff` (White) | `#00966e` (Green) | `#d62612` (Red) |
| **BF** | Burkina Faso | `#ef3340` (Red) | `#009e49` (Green) | `#fcd116` (Yellow) |
| **BI** | Burundi | `#ce1126` (Red) | `#10c25a` (Green) | `#ffffff` (White) |
| **CV** | Cabo Verde | `#0038a8` (Blue) | `#ffffff` (White) | `#ce1126` (Red) |
| **KH** | Cambodia | `#032ea1` (Blue) | `#ffffff` (White) | `#e00025` (Red) |
| **CM** | Cameroon | `#007a5e` (Green) | `#ce1126` (Red) | `#fcd116` (Yellow) |
| **CF** | Central African Republic | `#003082` (Blue) | `#ffffff` (White) | `#289728` (Green) |
| **TD** | Chad | `#002664` (Blue) | `#fecb00` (Yellow) | `#c60c30` (Red) |
| **CL** | Chile | `#0039a6` (Blue) | `#ffffff` (White) | `#d52b1e` (Red) |
| **CO** | Colombia | `#fcd116` (Yellow) | `#003893` (Blue) | `#ce1126` (Red) |
| **KM** | Comoros | `#3a7d44` (Green) | `#ffffff` (White) | `#3a53a4` (Blue) |
| **CD** | Congo, Dem. Rep. | `#007fff` (Blue) | `#f7d117` (Yellow) | `#ce1126` (Red) |
| **CG** | Congo, Rep. | `#009543` (Green) | `#fbde4a` (Yellow) | `#dc241f` (Red) |
| **CR** | Costa Rica | `#002b7f` (Blue) | `#ffffff` (White) | `#ce1126` (Red) |
| **CI** | Cote d'Ivoire | `#f77f00` (Orange) | `#ffffff` (White) | `#009e60` (Green) |
| **HR** | Croatia | `#ff0000` (Red) | `#ffffff` (White) | `#0000ff` (Blue) |
| **CU** | Cuba | `#00259c` (Blue) | `#ffffff` (White) | `#cc0d0d` (Red) |
| **CY** | Cyprus | `#ffffff` (White) | `#d47000` (Orange) | `#375225` (Green) |
| **CZ** | Czechia | `#ffffff` (White) | `#11457e` (Blue) | `#d7141a` (Red) |
| **DJ** | Djibouti | `#6ab2e7` (Blue) | `#ffffff` (White) | `#12ad2b` (Green) |
| **DM** | Dominica | `#006b3f` (Green) | `#fcd116` (Yellow) | `#d21034` (Red) |
| **DO** | Dominican Republic | `#00205b` (Blue) | `#ffffff` (White) | `#ba0c2f` (Red) |
| **EC** | Ecuador | `#ffdd00` (Yellow) | `#001489` (Blue) | `#da291c` (Red) |
| **EG** | Egypt | `#ce1126` (Red) | `#ffffff` (White) | `#000000` (Black) |
| **SV** | El Salvador | `#0047ab` (Blue) | - | `#ffffff` (White) |
| **GQ** | Equatorial Guinea | `#3e9a44` (Green) | `#ffffff` (White) | `#e41e20` (Red) |
| **ER** | Eritrea | `#0bc20b` (Green) | `#da121a` (Red) | `#249edc` (Blue) |
| **EE** | Estonia | `#0072ce` (Blue) | `#000000` (Black) | `#ffffff` (White) |
| **SZ** | Eswatini | `#3e5eb9` (Blue) | `#feb208` (Yellow) | `#b10c0c` (Red) |
| **ET** | Ethiopia | `#078930` (Green) | `#fcd116` (Yellow) | `#da121a` (Red) |
| **FJ** | Fiji | `#62b5e5` (Blue) | `#ffffff` (White) | `#ce1126` (Red) |
| **GA** | Gabon | `#009e60` (Green) | `#fcd116` (Yellow) | `#3a75c4` (Blue) |
| **GM** | Gambia | `#ce1126` (Red) | `#0c1c8c` (Blue) | `#3a7728` (Green) |
| **GE** | Georgia | `#ffffff` (White) | - | `#ff0000` (Red) |
| **GH** | Ghana | `#da121a` (Red) | `#fcd116` (Yellow) | `#006b3f` (Green) |
| **GR** | Greece | `#0d5eaf` (Blue) | - | `#ffffff` (White) |
| **GD** | Grenada | `#ce1126` (Red) | `#fcd116` (Yellow) | `#007a5e` (Green) |
| **GT** | Guatemala | `#4997d0` (Blue) | - | `#ffffff` (White) |
| **GN** | Guinea | `#ce1126` (Red) | `#fcd116` (Yellow) | `#009460` (Green) |
| **GW** | Guinea-Bissau | `#ce1126` (Red) | `#fcd116` (Yellow) | `#009e49` (Green) |
| **GY** | Guyana | `#009e49` (Green) | `#fcd116` (Yellow) | `#ce1126` (Red) |
| **HT** | Haiti | `#00209f` (Blue) | - | `#d21034` (Red) |
| **HN** | Honduras | `#0073cf` (Blue) | - | `#ffffff` (White) |
| **HU** | Hungary | `#ce1126` (Red) | `#ffffff` (White) | `#436f4d` (Green) |
| **IS** | Iceland | `#02529c` (Blue) | `#ffffff` (White) | `#dc1e35` (Red) |
| **IR** | Iran | `#239f40` (Green) | `#ffffff` (White) | `#da0000` (Red) |
| **IQ** | Iraq | `#ce1126` (Red) | `#ffffff` (White) | `#000000` (Black) |
| **IL** | Israel | `#0038a8` (Blue) | - | `#ffffff` (White) |
| **JM** | Jamaica | `#007749` (Green) | `#ffb81c` (Yellow) | `#000000` (Black) |
| **JO** | Jordan | `#000000` (Black) | `#ffffff` (White) | `#007a3d` (Green) |
| **KZ** | Kazakhstan | `#00afca` (Cyan) | - | `#fecb00` (Yellow) |
| **KE** | Kenya | `#000000` (Black) | `#bb0000` (Red) | `#006600` (Green) |
| **KI** | Kiribati | `#ce1126` (Red) | `#ffffff` (White) | `#00247d` (Blue) |
| **XK** | Kosovo | `#244391` (Blue) | `#d0a650` (Yellow) | `#ffffff` (White) |
| **KW** | Kuwait | `#007a3d` (Green) | `#ffffff` (White) | `#ce1126` (Red) |
| **KG** | Kyrgyzstan | `#e41e20` (Red) | - | `#fecb00` (Yellow) |
| **LA** | Laos | `#ce1126` (Red) | `#002868` (Blue) | `#ffffff` (White) |
| **LV** | Latvia | `#9e3039` (Maroon) | - | `#ffffff` (White) |
| **LB** | Lebanon | `#ed1c24` (Red) | `#ffffff` (White) | `#00a651` (Green) |
| **LS** | Lesotho | `#00209f` (Blue) | `#ffffff` (White) | `#009543` (Green) |
| **LR** | Liberia | `#bf0a30` (Red) | `#ffffff` (White) | `#002868` (Blue) |
| **LY** | Libya | `#e41e20` (Red) | `#000000` (Black) | `#239e46` (Green) |
| **LI** | Liechtenstein | `#002b7f` (Blue) | `#ffb81c` (Gold) | `#ce1126` (Red) |
| **LT** | Lithuania | `#fdb913` (Yellow) | `#006a44` (Green) | `#c1272d` (Red) |
| **LU** | Luxembourg | `#ea1c24` (Red) | `#ffffff` (White) | `#00a3e0` (Light Blue) |
| **MG** | Madagascar | `#ffffff` (White) | `#fc3d39` (Red) | `#007a3d` (Green) |
| **MW** | Malawi | `#000000` (Black) | `#ce1126` (Red) | `#397c31` (Green) |
| **MV** | Maldives | `#d21034` (Red) | `#ffffff` (White) | `#007e3a` (Green) |
| **ML** | Mali | `#14b53a` (Green) | `#fcd116` (Yellow) | `#ce1126` (Red) |
| **MT** | Malta | `#ffffff` (White) | - | `#d62612` (Red) |
| **MH** | Marshall Islands | `#0038a8` (Blue) | `#ffffff` (White) | `#dd7500` (Orange) |
| **MR** | Mauritania | `#006233` (Green) | `#ffc400` (Yellow) | `#d01c1c` (Red) |
| **MU** | Mauritius | `#ea1c2c` (Red) | `#1a206c` (Blue) | `#ffcd00` (Yellow) |
| **FM** | Micronesia | `#65b3e2` (Blue) | - | `#ffffff` (White) |
| **MD** | Moldova | `#002f6c` (Blue) | `#fecb00` (Yellow) | `#cc092f` (Red) |
| **MC** | Monaco | `#ce1126` (Red) | - | `#ffffff` (White) |
| **MN** | Mongolia | `#e01021` (Red) | `#0033a0` (Blue) | `#fecb00` (Yellow) |
| **ME** | Montenegro | `#c41230` (Red) | - | `#d5a848` (Gold) |
| **MA** | Morocco | `#c1272d` (Red) | - | `#006233` (Green) |
| **MZ** | Mozambique | `#009739` (Green) | `#000000` (Black) | `#d21034` (Red) |
| **MM** | Myanmar | `#fecb00` (Yellow) | `#34b234` (Green) | `#ea212d` (Red) |
| **NA** | Namibia | `#003580` (Blue) | `#ffffff` (White) | `#d21034` (Red) |
| **NR** | Nauru | `#002b7f` (Blue) | `#ffffff` (White) | `#ffc72c` (Yellow) |
| **NP** | Nepal | `#dc143c` (Red) | `#ffffff` (White) | `#0038a8` (Blue) |
| **NZ** | New Zealand | `#00247d` (Blue) | `#ffffff` (White) | `#cc142b` (Red) |
| **NI** | Nicaragua | `#0067c6` (Blue) | - | `#ffffff` (White) |
| **NE** | Niger | `#e05206` (Orange) | `#ffffff` (White) | `#0db134` (Green) |
| **NG** | Nigeria | `#008751` (Green) | - | `#ffffff` (White) |
| **KP** | North Korea | `#ed1c24` (Red) | `#ffffff` (White) | `#024fa2` (Blue) |
| **MK** | North Macedonia | `#d20000` (Red) | - | `#f8e000` (Yellow) |
| **PW** | Palau | `#4a90e2` (Blue) | - | `#fddb00` (Yellow) |
| **PS** | Palestine | `#000000` (Black) | `#ffffff` (White) | `#007a3d` (Green) |
| **PA** | Panama | `#00205b` (Blue) | `#ffffff` (White) | `#da291c` (Red) |
| **PG** | Papua New Guinea | `#000000` (Black) | `#da291c` (Red) | `#fcd116` (Yellow) |
| **PY** | Paraguay | `#d52b1e` (Red) | `#ffffff` (White) | `#0038a8` (Blue) |
| **PE** | Peru | `#d91023` (Red) | - | `#ffffff` (White) |
| **PT** | Portugal | `#006600` (Green) | - | `#ff0000` (Red) |
| **QA** | Qatar | `#8a1538` (Maroon) | - | `#ffffff` (White) |
| **RO** | Romania | `#002b7f` (Blue) | `#fcd116` (Yellow) | `#ce1126` (Red) |
| **RW** | Rwanda | `#00a1de` (Blue) | `#fad201` (Yellow) | `#20603d` (Green) |
| **KN** | Saint Kitts and Nevis | `#009e49` (Green) | `#000000` (Black) | `#ce1126` (Red) |
| **LC** | Saint Lucia | `#65b3e2` (Blue) | `#fcd116` (Yellow) | `#000000` (Black) |
| **VC** | Saint Vincent | `#00209f` (Blue) | `#fcd116` (Yellow) | `#009e49` (Green) |
| **WS** | Samoa | `#ce1126` (Red) | `#002b7f` (Blue) | `#ffffff` (White) |
| **SM** | San Marino | `#ffffff` (White) | - | `#5da1d4` (Blue) |
| **ST** | Sao Tome and Principe | `#009e49` (Green) | `#fcd116` (Yellow) | `#ce1126` (Red) |
| **SA** | Saudi Arabia | `#006c35` (Green) | - | `#ffffff` (White) |
| **SN** | Senegal | `#00853f` (Green) | `#fdef42` (Yellow) | `#e31b23` (Red) |
| **RS** | Serbia | `#c6363c` (Red) | `#0c4076` (Blue) | `#ffffff` (White) |
| **SC** | Seychelles | `#003f87` (Blue) | `#fcd116` (Yellow) | `#d21034` (Red) |
| **SL** | Sierra Leone | `#1eb53a` (Green) | `#ffffff` (White) | `#00209f` (Blue) |
| **SK** | Slovakia | `#ffffff` (White) | `#0b4ea2` (Blue) | `#ee1c25` (Red) |
| **SI** | Slovenia | `#ffffff` (White) | `#002bff` (Blue) | `#ff0000` (Red) |
| **SB** | Solomon Islands | `#0051ba` (Blue) | `#fcd116` (Yellow) | `#215b33` (Green) |
| **SO** | Somalia | `#4189dd` (Blue) | - | `#ffffff` (White) |
| **SS** | South Sudan | `#000000` (Black) | `#da121a` (Red) | `#078930` (Green) |
| **ES** | Spain | `#aa151b` (Red) | - | `#f1bf00` (Yellow) |
| **LK** | Sri Lanka | `#8d1b3d` (Maroon) | `#ffbe29` (Gold) | `#005f43` (Green) |
| **SD** | Sudan | `#da121a` (Red) | `#ffffff` (White) | `#000000` (Black) |
| **SR** | Suriname | `#377e3f` (Green) | `#ffffff` (White) | `#b40a2d` (Red) |
| **CH** | Switzerland | `#da291c` (Red) | - | `#ffffff` (White) |
| **SY** | Syria | `#ce1126` (Red) | `#ffffff` (White) | `#000000` (Black) |
| **TJ** | Tajikistan | `#cc0000` (Red) | `#ffffff` (White) | `#006600` (Green) |
| **TZ** | Tanzania | `#1eb53a` (Green) | `#000000` (Black) | `#00a3e0` (Blue) |
| **TL** | Timor-Leste | `#dc241f` (Red) | `#ffc72c` (Yellow) | `#000000` (Black) |
| **TG** | Togo | `#006a4e` (Green) | `#ffce00` (Yellow) | `#d21034` (Red) |
| **TO** | Tonga | `#c10024` (Red) | - | `#ffffff` (White) |
| **TT** | Trinidad and Tobago | `#da121a` (Red) | `#000000` (Black) | `#ffffff` (White) |
| **TN** | Tunisia | `#e70013` (Red) | - | `#ffffff` (White) |
| **TR** | Turkey | `#e30a17` (Red) | - | `#ffffff` (White) |
| **TM** | Turkmenistan | `#239e46` (Green) | `#ce1126` (Red) | `#ffffff` (White) |
| **TV** | Tuvalu | `#5b97c8` (Blue) | `#fcd116` (Yellow) | `#ffffff` (White) |
| **UG** | Uganda | `#000000` (Black) | `#fcdc04` (Yellow) | `#d90000` (Red) |
| **UA** | Ukraine | `#0057b7` (Blue) | - | `#ffd700` (Yellow) |
| **AE** | UAE | `#00732f` (Green) | `#ffffff` (White) | `#000000` (Black) |
| **UY** | Uruguay | `#0038a8` (Blue) | `#ffffff` (White) | `#fcd116` (Yellow) |
| **UZ** | Uzbekistan | `#00a1de` (Blue) | `#ffffff` (White) | `#1eb53a` (Green) |
| **VU** | Vanuatu | `#d21034` (Red) | `#009543` (Green) | `#000000` (Black) |
| **VE** | Venezuela | `#ffcc00` (Yellow) | `#00247d` (Blue) | `#cf142b` (Red) |
| **YE** | Yemen | `#ce1126` (Red) | `#ffffff` (White) | `#000000` (Black) |
| **ZM** | Zambia | `#198a00` (Green) | `#ef7d00` (Orange) | `#000000` (Black) |
| **ZW** | Zimbabwe | `#319234` (Green) | `#ffd200` (Yellow) | `#de2010` (Red) |

*Default fallback for unknown countries: `#ffffff` to `#a1a1aa` (Gray scale).*
