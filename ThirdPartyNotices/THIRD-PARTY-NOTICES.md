# Third-Party Notices

| Component | Upstream | Source URL | Version/Retrieval | License | Local files covered | Notice requirements |
|---|---|---|---|---|---|---|
| MakeHuman core assets (development avatars) | MakeHuman Community | https://static.makehumancommunity.org/about/license.html | Pending capture | CC0 (project-stated for core assets) | desktop/Jarvis.Desktop/Assets/Avatars/* | Preserve local license reference and verify non-core assets individually |
| Kokoro-82M model/runtime | hexgrad | https://huggingface.co/hexgrad/Kokoro-82M | Pending runtime integration | Apache-2.0 | Local Kokoro runtime/models under Assets/Voices (future) | Include Apache notice and attribution for transitive dependencies |
| WebView2 | Microsoft | https://www.nuget.org/packages/Microsoft.Web.WebView2 | 1.0.2849.39 | Microsoft package license | desktop/Jarvis.Desktop runtime dependency | Include package attribution via installer/package notices as required |

## Notes

- Do not mark community-contributed MakeHuman assets as CC0 unless the individual asset record confirms it.
- Do not enable redistributionAllowed in avatar manifests until asset licensing is verified for your deployment model.
