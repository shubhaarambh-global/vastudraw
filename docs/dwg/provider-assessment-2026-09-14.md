# DWG provider assessment — 2026-09-14

## Open Design Alliance Drawings SDK

Status: **preferred production candidate; external licensed runtime required**.

Evidence: <https://www.opendesign.com/products/drawings> and <https://www.opendesign.com/oda-membership>. ODA documents native DWG create/edit/save support, current AC1032-era DWG support, and Python wrappers for Drawings SDK under applicable membership.

Repository decision: no ODA binary is bundled. Production remains disabled until an installed runtime passes the qualification contract and real CAD interoperability tests.

## GNU LibreDWG 0.13.4

Status: **not eligible for R2018 production write**.

Evidence: <https://www.gnu.org/software/libredwg/manual/html_node/Encoding.html> and <https://www.gnu.org/software/libredwg/manual/html_node/Programs.html>. Current documentation states useful/default writing is R2000 or older; later generations remain incomplete/experimental.

License: GPL-3.0-or-later.

Repository decision: do not silently fall back to LibreDWG for modern DWG output.
