# Apex Racing Hub

Original static motorsport affiliate starter website inspired by the general feature set of racing-fans.pages.dev. It does not copy the reference site's proprietary source, branding or editorial text.

## Deploy
Upload the contents of this directory to a GitHub repository and connect that repository to Cloudflare Pages. Build command: leave blank. Output directory: `/` (or use Cloudflare Pages direct upload). Also works with Netlify and most static hosts.

## Amazon affiliate setup
In `index.html`, replace `const AMAZON_ASSOCIATES_TAG=''` with your *approved* Associates tracking ID, for example `const AMAZON_ASSOCIATES_TAG='yourtag-20'`. Do not add a made-up ID. Links are currently Amazon product searches and do not earn commission without an approved tag. Confirm compliance with Amazon Associates Operating Agreement and current program policies, including rules on product data and disclosures. Do not claim an affiliate relationship before approved.

## Data
Upcoming Formula 1 events use the public Jolpica API from the browser; other series and standings link to official sites. This is not a full live-results service. To expand, obtain permitted racing data feeds/API credentials and implement scheduled ingestion with caching and rate limits.

## Before launch
- Choose site name and domain; update title and branding.
- Replace placeholder contact email and complete the privacy policy.
- Review official external links and current-year F1 standings link each season.
- Add original editorial guides and legally licensed images.
- Add a sitemap using the actual deployed domain.
- Add approved affiliate tag and verify links.
- Set up analytics and Search Console after publication.
