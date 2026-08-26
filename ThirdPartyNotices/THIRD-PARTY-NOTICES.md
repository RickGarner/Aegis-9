# Third-Party Notices

| Component | Upstream | Source URL | Version/Retrieval | License | Local files covered | Notice requirements |
|---|---|---|---|---|---|---|
| MakeHuman core assets (development avatars) | MakeHuman Community | https://static.makehumancommunity.org/about/license.html | Pending capture | CC0 (project-stated for core assets) | desktop/Jarvis.Desktop/Assets/Avatars/* | Preserve local license reference and verify non-core assets individually |
| Kokoro-82M model/runtime | hexgrad | https://huggingface.co/hexgrad/Kokoro-82M | Pending runtime integration | Apache-2.0 | Local Kokoro runtime/models under Assets/Voices (future) | Include Apache notice and attribution for transitive dependencies |
| ActorCore free actors | Reallusion | https://actorcore.reallusion.com/ | Downloaded 2026-08-26; account/free-content terms pending verification | ActorCore/Reallusion terms | desktop/Jarvis.Desktop/Assets/Avatars/* | Local-use-only until the specific account and actor terms are verified; do not redistribute |
| Wolforge Jarvis avatar | Jarvis project asset | Local supplied package under resources/avatars/wolforge | Integrated 2026-08-26 | Project-supplied asset; verify final terms | desktop/Jarvis.Desktop/Assets/Avatars/male/wolforge_jarvis_avatar.glb and female equivalent | Local-use-only; redistribution disabled pending confirmation |
| model-viewer | Google | https://github.com/google/model-viewer | 4.0.0, downloaded 2026-08-26 | Apache-2.0 | desktop/Jarvis.Desktop/Assets/AvatarHost/vendor/model-viewer.min.js | Preserve upstream Apache notice if distributed |
| WebView2 | Microsoft | https://www.nuget.org/packages/Microsoft.Web.WebView2 | 1.0.2849.39 | Microsoft package license | desktop/Jarvis.Desktop runtime dependency | Include package attribution via installer/package notices as required |

## Notes

- Do not mark community-contributed MakeHuman assets as CC0 unless the individual asset record confirms it.
- Do not enable redistributionAllowed in avatar manifests until asset licensing is verified for your deployment model.
