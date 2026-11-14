# UI mockup prompt (for Sachin)

Paste everything below the line into a new Claude chat to discuss the frontend before anyone builds it.
Written 14 Nov 2026, 10:10 IST. Source of truth: `06_PLAN_Eye_of_the_Storm.md` and `07_BACKEND_RESOURCE_REGISTRY.pdf`.

---

I'm Sachin, mentoring team SpaceBros at NASA Space Apps 2026 (challenge: "Dancing with the SARs").
The hackathon runs now until Sun 15 Nov, 20:00 IST. I want to DISCUSS the frontend UI with you
before anyone builds it, then turn the agreed direction into a mockup.

WHAT WE'RE BUILDING
A NISAR-centred coastal-hazard interface for the Bay of Bengal coast of Andhra Pradesh
(Godavari delta: Konaseema, West Godavari, Kakinada). Cyclone Arnab (landfall near Narsapur,
late 27 / early 28 Oct 2026 IST - exact time being confirmed from IMD) is the proof event. The data
already exists but is scattered across many portals and logins; we put it on one screen, with a
date, a source, a credit line and one plain note on what each layer cannot tell you. NISAR radar
must stay visibly the core - judges score how we use NISAR.

USERS (in priority order)
1. District disaster cell and agriculture / fisheries officers: "where to send teams first" by
   mandal, plus a one-page downloadable brief. Laptop in the office, phone in the field.
2. Cyclone researchers: the radar eye, numbers with ± uncertainty.
3. Teachers, journalists, the public: what radar can and can't see.

FIXED PARTS OF THE PAGE
- A layer panel built from a registry (manifest.json): layers grouped Before / During / After,
  each showing date, source, credit and a one-line limit. Hazards we haven't built (earthquake,
  oil spill, wildfire) appear greyed as "coming next".
- An alerts strip: GDACS loaded live, plus a dated snapshot of India's NDMA SACHET alerts
  (SACHET's feed blocks browser access, so our pipeline saves it). Always show the snapshot time.
- A guided story of Arnab in 6 parts:
  Hero (radar eye image)
  1 From above (optical image + cyclone track)
  2 Under the clouds (swipe: calm sea 15 Oct vs storm 27 Oct)
  3 How rough (difference map + radial profile chart; hovering the chart moves a ring on the map)
  4 The shore (delta swipe 23 Oct -> 4 Nov; "likely flooded" classes; mandal outlines; L/S-band toggle)
  5 What radar cannot tell you (4 claims, 4 verdicts, slider comparing 24 cm and 9 cm waves)
  6 About (data, methods, limits, credits)
- Download brief: a one-page summary per mandal.

CONSTRAINTS
Static site on GitHub Pages: Leaflet + a swipe plugin, Scrollama, Chart.js, no server.
Every map is a PNG with bounds; every number comes from JSON. Live layers (GIBS imagery,
Open-Meteo waves and river flow, GDACS) load directly in the browser. Whole page under 15 MB.
On mobile, text stacks above the map. Every class label starts with "likely".
Every caption carries its credit line. English now, room for Telugu later.

MY DESIGN TASTE
Data shown simply and graphically (visual numbers over text). Muted, calm colours that don't
dominate, but a clear brand identity. Almost no stock or AI-looking imagery; the radar images
are the visuals.

HOW I WANT TO WORK
1. First ask me the 3-4 questions that most change the layout (e.g. map-first app vs. scroll
   story; how the layer panel and the story share the screen; what a district officer sees in
   the first 5 seconds).
2. Then propose 2-3 distinct layout directions as rough wireframes, each with a short trade-off,
   and say which you'd pick.
3. After I pick, make the mockup: desktop and mobile versions of the main screen, the layer
   panel open, and one story chapter (4, The shore).
4. Push back if something won't fit in the time left or would hide NISAR.
Gates: Sat 23:00 sea chapter live, Sun 11:30 MVP, Sun 16:00 freeze, Sun 20:00 submit.
