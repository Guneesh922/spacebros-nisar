/* =====================================================================
   FINDINGS  (plain-language copy for the "What happened" section)
   ---------------------------------------------------------------------
   THIS IS THE ONLY PLACE WHERE LAY-READER WORDS LIVE.
   Later, replace this whole object with a backend-generated file, e.g.
   data/processed/findings.json, loaded into window.FINDINGS before dash.js.
   Numbers are NOT typed here: strings use {placeholders} that dash.js
   fills from mandal_rank.json, profile.json and the manifest.
   Optional per-mandal overrides: FINDINGS.mandals["Narasapuram"] = {
     headline, meaning, confidence: "high|medium|low", confidence_note }.
   Everything derived from sample files is tagged "Sample values" on screen.
   ===================================================================== */
window.FINDINGS = {
  meta: {
    schema: "findings-mockup-0",
    source: "neutral fallback text only; real summaries come from data/processed/findings/*.json",
    sample: true
  },

  /* Nicknames shown next to the official mandal spelling */
  aliases: { "Narasapuram": "Narsapur" },

  /* Neutral fallback only. The summary itself comes from data/processed/findings/*.json. */
  intro: {
    title: "Latest radar pass",
    lead: "Summary not available yet.",
    landfall_unknown: "",
    how_to_read: "Click a mandal on the map or in the list. Each box says what we found, how sure we are, and what radar cannot tell you."
  },

  ranking: {
    title: "Where help is needed first",
    sub: "Mandals with the largest share of land that was probably flooded.",
    reading_help: "This is a list of where to look first. It is not a count of damage.",
    legend_water: "Probably open water",
    legend_crops: "Probably flooded crops",
    legend_normal: "A normal fortnight",
    legend_err: "Give or take"
  },

  /* {name} {lik} {normal} {times} {err} {water} {crops} */
  mandal: {
    headline: "About {lik} in every 100 acres of {name} were probably under floodwater.",
    meaning: "In a normal fortnight it is about {normal} in 100. That is {times} the usual share.",
    meaning_less: "In a normal fortnight it is about {normal} in 100. That is lower than usual.",
    meaning_same: "In a normal fortnight it is about {normal} in 100. That is about the same as usual.",
    split: "{water} of the {lik} looks like open water. {crops} looks like flooded fields with crops.",
    err: "Give or take {err} out of 100.",
    conf_high: "Fairly sure",
    conf_medium: "Moderately sure",
    conf_low: "Less sure",
    conf_note_high: "The radar signal was clear here.",
    conf_note_medium: "The signal was clear, but small errors could move this number a little.",
    conf_note_low: "The signal was weak here. Treat this as a hint, and check on the ground.",
    cannot: "Radar cannot tell you how deep the water was, how long it stayed, or whether homes or crops were damaged. Water under thick crops can be missed, so the real flooded share may be higher."
  },

  /* Event wording (landfall, eye profile, wind, before/after, other-water caveat) is NOT here:
     it comes from data/processed/events.json `story` and shows only with an event chip or in the Events archive. */

  confidence: {
    title: "How sure are we?",
    items: [
      "We say \"probably\" on purpose. Radar change points to flood water. Nobody has checked it on the ground.",
      "The radar could see through clouds and rain, so the picture is clear.",
      "Mandal numbers are shares of each mandal. They come with a give-or-take figure."
    ]
  },

  /* verdict: yes | partly | no. Draft wording, to be reviewed by a domain expert (see docs/PLACEHOLDERS.md section 7) */
  cannot_tell: {
    title: "What radar cannot tell you",
    draft_tag: "Draft: to be reviewed",
    items: [
      { verdict: "yes",    claim: "Radar can see the sea under clouds.",
        why: "It sends its own signal, so cloud does not block it." },
      { verdict: "partly", claim: "Radar can see flood water under crops.",
        why: "Water under crop stems shows up. Thick crops can hide some water, so some floods are missed." },
      { verdict: "no",     claim: "Radar tells you how fast the wind blew.",
        why: "A rougher sea looks brighter. That is a clue, not a speed." },
      { verdict: "no",     claim: "Radar tells you how deep the water is.",
        why: "It shows where the surface looks like open water. It does not measure depth or what was lost." }
    ]
  },

  /* permanent line on the What happened tab; links come from data/events/*.json official_links */
  official: { text: "Not an official warning \u2014 follow IMD and APSDMA." },

  tips: {
    db: "Radar brightness is measured in decibels (dB). A brighter sea means rougher water.",
    err: "How far the true value could be from the number shown."
  },

  link_to_data: {
    title: "Want the raw numbers?",
    text: "The full table, the scene list, the alerts and the files to download are in the section for officials and researchers.",
    button: "Open the data section"
  },

  /* Map captions: Shows / Cannot show / Source (same three rows as the app). */
  captions: {
    radar_sea: { shows: "Radar brightness of the sea on {date} (VV, dB). Brighter sea is rougher.", cant: "Wind speed. Brightness is a clue to roughness only.", src: "NISAR L-band, NASA/JPL-Caltech and ISRO via ASF DAAC", sample: "Quick-look sample" },
    share:  { shows: "How much of each mandal was probably flooded, over the {date} radar picture.", cant: "How deep the water was, or any damage.", src: "SpaceBros analysis of NISAR L-band, NASA/JPL-Caltech and ISRO via ASF DAAC", sample: "Sample values" },
    radar:  { shows: "Radar brightness of the land on {date} (HH, brightness in dB). Dark patches can be water.", cant: "Ground truth. This is one date only.", src: "NISAR L-band, NASA/JPL-Caltech and ISRO via ASF DAAC", sample: "Quick-look sample" },
    swipe:  { shows: "Radar brightness of the {what} on {before} (before, left) and {after} (after, right).", cant: "Wet soil apart from shallow water.", src: "NISAR L-band, NASA/JPL-Caltech and ISRO via ASF DAAC", sample: "Quick-look sample" },
    eye:    { shows: "Radar brightness of the sea on {date} (VV, dB). Brighter sea is rougher. The dark hole is the calm eye.", cant: "Wind speed. Brightness is a clue to roughness only.", src: "NISAR L-band, NASA/JPL-Caltech and ISRO via ASF DAAC. Track: IMD bulletins", sample: "Quick-look sample" },
    custom: { shows: "The layers ticked in the layer list.", cant: "See the Limit column for each layer.", src: "Credit for each layer is in the layer list", sample: null }
  }
};
