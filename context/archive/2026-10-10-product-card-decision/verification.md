# Product Card Browser Verification

- **Date**: 2026-10-11
- **Scope**: Manual criteria 2.3, 2.4, 3.3, 3.4, 3.6, and 4.2–4.4
- **Environment**: Django development server with an isolated temporary SQLite database
- **Browsers/data**: Local Cursor browser; non-staff and staff test users; Gap, Premium, and Budget shampoo fixtures

## Results

- **PASS — 2.3**: Gap shampoo had Rossmann points two days ago and today with no point yesterday. One polyline joined the two points across the missing day. The chart retained all 30 calendar slots; 29 dividers were separately visible because the first slot coincided with the Y axis. DOZ showed `No price` today and retained its stored shop link. `Lowest recorded price` showed the out-of-window 10.00 PLN observation.
- **PASS — 2.4**: The card showed the product name, shop prices, one inline SVG chart, and shop links. It did not show description or availability.
- **PASS — 3.3**: A non-staff user signed in, saw a name-only home list, clicked Gap shampoo, and reached `/products/1/` in the same tab. The home list contained no `PLN`, `Cheapest`, or `No price`.
- **PASS — 3.4**: A staff user saw the add-product link on the home page.
- **PASS — 3.6**: Home links from the sign-in page after authentication, a product card, and `/products/` all returned to `/` in the same tab.
- **PASS — 4.2 (amended)**: Premium shampoo used a 30.00 PLN axis floor for 80.00 and 90.00 PLN observations, ended at 90.00, used the adaptive 5.00 PLN interval, and showed the Rossmann legend.
- **PASS — 4.3 (amended)**: Budget shampoo used a 0.00 PLN axis floor for 18.00 and 19.99 PLN observations, used the adaptive 1.00 PLN interval, and showed the Gemini legend.
- **PASS — 4.4**: The Rossmann card link had `target="_blank"` and `rel="noopener noreferrer"` and opened a new browser tab. Product names on `/products/` had no `target="_blank"` and opened their cards in the same tab.

The adaptive interval observations follow the implementation-review amendment in `plan.md`, which supersedes the original fixed 10 PLN interval.

## Session screenshots

- Gap shampoo card: `C:\Users\marci\AppData\Local\Temp\cursor\screenshots\gap-shampoo-card.png`
- Staff product list: `C:\Users\marci\AppData\Local\Temp\cursor\screenshots\staff-product-list.png`
- Premium shampoo axis: `C:\Users\marci\AppData\Local\Temp\cursor\screenshots\premium-shampoo-axis.png`
- Budget shampoo axis: `C:\Users\marci\AppData\Local\Temp\cursor\screenshots\budget-shampoo-axis.png`
