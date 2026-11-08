/**
 * Race venue presets. Coordinates as stated in each place's English Wikipedia article
 * (coordinates template), read on 2026-11-09. Coordinates are area-level, not start lines.
 * Metro Manila venues use the urban wind exponents; Clark uses the rural set (SCIENCE.md 4).
 */
export interface Venue {
  id: string;
  name: string;
  lat: number;
  lon: number;
  urban: boolean;
  source: string;
}

export const VENUES: Venue[] = [
  {
    id: "qmc",
    name: "Quezon Memorial Circle, Quezon City",
    lat: 14.651417,
    lon: 121.04917,
    urban: true,
    source: "https://en.wikipedia.org/wiki/Quezon_Memorial_Circle",
  },
  {
    id: "moa",
    name: "SM Mall of Asia, Pasay",
    lat: 14.535,
    lon: 120.98194,
    urban: true,
    source: "https://en.wikipedia.org/wiki/SM_Mall_of_Asia",
  },
  {
    id: "bgc",
    name: "Bonifacio Global City, Taguig",
    lat: 14.550806,
    lon: 121.050972,
    urban: true,
    source: "https://en.wikipedia.org/wiki/Bonifacio_Global_City",
  },
  {
    id: "up-diliman",
    name: "University of the Philippines Diliman, Quezon City",
    lat: 14.654925,
    lon: 121.06485,
    urban: true,
    source:
      "https://en.wikipedia.org/wiki/University_of_the_Philippines_Diliman",
  },
  {
    id: "filinvest",
    name: "Filinvest City, Muntinlupa",
    lat: 14.417472,
    lon: 121.04194,
    urban: true,
    source: "https://en.wikipedia.org/wiki/Filinvest_City",
  },
  {
    id: "clark",
    name: "Clark Freeport Zone, Pampanga",
    lat: 15.18493,
    lon: 120.5394,
    urban: false,
    source:
      "https://en.wikipedia.org/wiki/Clark_Freeport_and_Special_Economic_Zone",
  },
];
