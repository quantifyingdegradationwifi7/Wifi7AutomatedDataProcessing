export const categories = [
  {
    name: "Overview & Summary",
    scenarios: [
      {
        id: 0,
        title: "Cross-Scenario Summary Table",
        image: "Figure 35 - Table summary showing cross-scenario degradation by environmental factor.png",
        locationImages: [],
        csvId: null,
        analysis: "Summary showing cross-scenario degradation across all tested environments. Across all 17 scenarios, 6 GHz demonstrated the highest resilience to interference and high contention, while 2.4 GHz was the most vulnerable. MLO frequently failed to deliver theoretical aggregation, defaulting to single-radio fallback modes."
      }
    ]
  },
  {
    name: "High User Density / Contention",
    scenarios: [
      {
        id: 4,
        title: "Scenario 4: AUT Mojo Cafe",
        image: "Figure 18 - Throughput and RSSI Box Plots for Scenario 4: AUT Mojo Cafe..png",
        locationImages: ["Scenario 4.1 - AUT Mojo Cafe.webp", "Scenario 4.2 - AUT Mojo Cafe.jpg"],
        csvId: "mojo",
        analysis: "The 6 GHz band retained 680.6 Mbps of its 932.9 Mbps baseline. In stark contrast, 2.4 GHz and 5 GHz throughputs collapsed. MLO performance was severely impacted, plummeting to 74.16 Mbps due to heavy active device contention and overlapping basic service sets (OBSS). The firmware failed to evaluate channel utilization, forcing a fallback to the highly congested 2.4 GHz band."
      },
      {
        id: 5,
        title: "Scenario 5: AUT Library",
        image: "Figure 19 - Throughput and RSSI Box Plots for Scenario 5: AUT Library..png",
        locationImages: ["Scenario 5 - AUT Library.webp"],
        csvId: "librarby",
        analysis: "Legacy bands experienced near-total throughput collapse (2.4 GHz and 5 GHz dropping to 0.07 Mbps and 24.44 Mbps). 6 GHz maintained 267.6 Mbps. MLO configuration failed entirely, yielding 0.27 Mbps due to an overwhelmed EMLSR fallback mechanism entering a sub-optimal switching loop."
      }
    ]
  },
  {
    name: "Structural / Material Blockage",
    scenarios: [
      {
        id: 6,
        title: "Scenario 6: Server Racks, Switches Off (WS Lab)",
        image: "Figure 20 - Throughput and RSSI Box Plots for Scenario 6: Server Rack, Switches Off (WS Lab).png",
        locationImages: ["Scenario 6 & 7 - WS Server Lab.webp", "Scenario 6 & 7.2 - WS Server Lab.webp"],
        csvId: "ws200_switched_off",
        analysis: "The 6 GHz band exhibited exceptional penetration performance, retaining 927.5 Mbps. 5 GHz saw minimal degradation, whereas 2.4 GHz halved. MLO degraded significantly to 553.2 Mbps, proving that differing attenuation profiles across bands confuse the firmware's link-switching logic."
      },
      {
        id: 8,
        title: "Scenario 8: Lecture Hall (Lecture Hall WG)",
        image: "Figure 21 - Throughput and RSSI Box Plots for Scenario 8: Lecture Hall (Lecture Hall WG)..png",
        locationImages: ["Section 8.1 - Lecture Hall WG.webp", "Section 8.2 - Lecture Hall WG.webp"],
        csvId: "wg403_vroom",
        analysis: "Non-line-of-sight signal attenuation was substantial across all high-frequency bands. 6 GHz dropped to 321 Mbps, matching 5 GHz. MLO was similarly hindered at 162.4 Mbps, suggesting hardware could not dynamically combine the highly attenuated signals to recover throughput."
      },
      {
        id: 11,
        title: "Scenario 11: Between Concrete Floors (Stairwell)",
        image: "Figure 22 - Throughput and RSSI Box Plots for Scenario 11: Between Concrete Floors (Stairwell)..png",
        locationImages: ["Scenario 11 - Reinforced Concrete Stairwell.jpg"],
        csvId: "artsblock_concrete",
        analysis: "Vertical propagation through reinforced concrete resulted in severe degradation. 6 GHz dropped to 361.9 Mbps, and 5 GHz to 375.5 Mbps. MLO recorded 218.7 Mbps, reflecting firmware-limited single-link fallback rather than true aggregation."
      },
      {
        id: 16,
        title: "Scenario 16: Underground Concrete Corner",
        image: "Figure 23 - Throughput and RSSI Box Plots for Scenario 16: Underground Concrete Corner (Basement)..png",
        locationImages: ["Scenario 16.1 - Basement Parking Corner.webp", "Scenario 16.2 - Basement Parking Corner.webp"],
        csvId: "backrooms",
        analysis: "Severe NLOS conditions caused a massive drop in 6 GHz (380 Mbps). MLO plummeted to 108.3 Mbps, exactly mirroring the 2.4 GHz standalone result, proving the firmware abandons high-capacity bands when faced with heavy obstruction."
      }
    ]
  },
  {
    name: "Specular Reflection (Glass)",
    scenarios: [
      {
        id: 10,
        title: "Scenario 10: Glass Elevator",
        image: "Figure 24 - Throughput and RSSI Box Plots for Scenario 10: Glass Elevator..png",
        locationImages: ["Scenario 10 - Glass Elevator.webp"],
        csvId: "wh_elevator_glassish",
        analysis: "The 6 GHz band maintained 548.9 Mbps. MLO performance was poor, averaging 108.6 Mbps. The ~40% degradation in higher frequencies is attributed to specular reflection and angle-of-incidence diffraction. MLO latched onto the heavily attenuated 2.4 GHz band."
      },
      {
        id: 15,
        title: "Scenario 15: Hallway with Glass Doors",
        image: "Figure 25 - Throughput and RSSI Box Plots for Scenario 15: Hallway with Glass Doors (WA Atrium).png",
        locationImages: ["Scenario 15.1 - WA Building Glass Atrium.webp", "Scenario 15.2 - WA Building Glass Atrium.webp"],
        csvId: "we_lvl3_hallway",
        analysis: "Both 5 GHz and 6 GHz dropped to 628.9 Mbps and 590.3 Mbps. MLO throughput was exceptionally poor at 71.75 Mbps. Heavy glass corridors induced complex multipath propagation, completely nullifying the benefits of Wi-Fi 7 MLO."
      }
    ]
  },
  {
    name: "Electromagnetic Interference",
    scenarios: [
      {
        id: 7,
        title: "Scenario 7: Server Rack, Switches On",
        image: "Figure 26 - Throughput and RSSI Box Plots for Scenario 7: Server Rack, Switches On (WS Lab)..png",
        locationImages: ["Scenario 6 & 7 - WS Server Lab.webp", "Scenario 6 & 7.2 - WS Server Lab.webp"],
        csvId: "ws200_switched_on",
        analysis: "Active enterprise equipment had minimal impact on 6 GHz (932.3 Mbps). MLO achieved 530.6 Mbps. 6 GHz demonstrated complete immunity to typical enterprise noise floors, but MLO inconsistent band-selection remains a limitation."
      },
      {
        id: 14,
        title: "Scenario 14: Recording Studio",
        image: "Figure 27 - Throughput and RSSI Box Plots for Scenario 14: Recording Studio..png",
        locationImages: ["Scenario 14.1 - Recording Studio.webp", "Scenario 14.2 - Recording Studio.webp"],
        csvId: "studio",
        analysis: "6 GHz proved most robust amidst heavy EMI, retaining 796 Mbps. 2.4 GHz and 5 GHz saw significant drops. MLO recorded 462.6 Mbps, providing stark evidence of sub-optimal alternating fallback mode rather than true multi-link aggregation."
      },
      {
        id: 17,
        title: "Scenario 17: Microwave On",
        image: "Figure 28 - Throughput and RSSI Box Plots for Scenario 17: Microwave On (WZ Level 7)..png",
        locationImages: ["Scenario 17 - WZ Level 7 (Microwave).webp"],
        csvId: "microwave_on",
        analysis: "Severe 2.4 GHz EMI from an active microwave dropped throughput to 138.8 Mbps. 6 GHz was completely unphased (925.7 Mbps). MLO alternated to yield 500.2 Mbps, showcasing that current hardware cannot effectively exploit 6 GHz's ISM noise immunity."
      }
    ]
  },
  {
    name: "Extreme Multipath (Faraday)",
    scenarios: [
      {
        id: 9,
        title: "Scenario 9: Metal Elevator",
        image: "Figure 29 - Throughput and RSSI Box Plots for Scenario 9: Metal Elevator..png",
        locationImages: ["Scenario 9 -Metal Elevator.webp"],
        csvId: "ws_5_to_4_elevator",
        analysis: "Performance plummeted universally. 6 GHz degraded to 78.37 Mbps, and MLO collapsed to 58.06 Mbps. The elevator cab acts as a Faraday cage, proving current firmware logic is fundamentally incapable of aggregating weak, highly reflected signals."
      }
    ]
  },
  {
    name: "Dynamic Mobility / Roaming",
    scenarios: [
      {
        id: 1,
        title: "Scenario 1: Below Escalator",
        image: "Figure 30 - Throughput and RSSI Box Plots for Scenario 1: Below Escalator (WZ Levels 1 to 3)..png",
        locationImages: ["Scenario 1 & 2.1 - WZ Level 3 Escalator.webp", "Scenario 1 & 2.2 - WZ Level 3 Escalator.webp"],
        csvId: "wz300_escalator",
        analysis: "6 GHz dropped to 638.5 Mbps. MLO performance collapsed to 19.2 Mbps due to severe multipath fading and signal scattering from moving metallic escalator steps. The router failed to aggregate stable links, locking onto a degraded single connection."
      },
      {
        id: 2,
        title: "Scenario 2: Next To Escalator",
        image: "Figure 31 - Throughput and RSSI Box Plots for Scenario 2: Next To Escalator (WZ Level 3)..png",
        locationImages: ["Scenario 1 & 2.1 - WZ Level 3 Escalator.webp", "Scenario 1 & 2.2 - WZ Level 3 Escalator.webp"],
        csvId: "wzlvl3_esc_onlvl3",
        analysis: "6 GHz maintained strong resilience (809.3 Mbps). MLO yielded 470.7 Mbps. The data confirmed the hardware's reliance on alternating single-radio mode rather than leveraging true multi-link aggregation capabilities."
      }
    ]
  },
  {
    name: "Long Distance / Path Loss",
    scenarios: [
      {
        id: 12,
        title: "Scenario 12: Bus Station (Outdoor)",
        image: "Figure 32 - Throughput and RSSI Box Plots for Scenario 12: Bus Station (Outdoor)..png",
        locationImages: ["Scenario 12.1 - Bus Station (Outdoor).webp", "Scenario 12.2 - Bus Station (Outdoor).webp"],
        csvId: "busstop",
        analysis: "6 GHz demonstrated clear superiority (447 Mbps) compared to 5 GHz (138.7 Mbps) and an unusable 2.4 GHz band. MLO achieved only 152.2 Mbps, dragged down by immature band-steering logic attempting to use the unusable legacy frequency."
      }
    ]
  },
  {
    name: "Acoustic / Localised Obstruction",
    scenarios: [
      {
        id: 3,
        title: "Scenario 3: Quiet Room",
        image: "Figure 33 - Throughput and RSSI Box Plots for Scenario 3: Quiet Room (WZ400)..png",
        locationImages: ["Scenario 3 - WZ400 Quiet Room.jpg"],
        csvId: "wz400_quiet_room",
        analysis: "6 GHz proved highly robust against human tissue absorption (302.9 Mbps). MLO yielded 296.7 Mbps. The stability indicates sufficient signal margin to overcome temporary NLOS conditions, but true simultaneous multi-link operation was not achieved."
      },
      {
        id: 13,
        title: "Scenario 13: Outside Soundproof Room",
        image: "Figure 34 - Throughput and RSSI Box Plots for Scenario 13: Outside Soundproof Room (WZ Level 9)..png",
        locationImages: ["Scenario 13 - Level 9 Soundsproof Room.webp"],
        csvId: "wz_lvl9_meetingroom",
        analysis: "Acoustic dampening materials heavily absorbed 5 GHz and 2.4 GHz, but 6 GHz showed exceptional resilience (930.2 Mbps). MLO yielded 643.5 Mbps, demonstrating that the connection remained sub-maximal compared to a standalone 6 GHz link."
      }
    ]
  }
];