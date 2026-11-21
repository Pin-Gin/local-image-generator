# 2026-11-22 ローカル画像生成：Redraw Role Separation v1 到達点と再開手順

Status: **EXPERIMENT / ONE USER-VISUALLY VERIFIED WARDROBE-STATE RESULT / BODY-QUALITY OPEN**  
対象: \`Pin-Gin/local-image-generator\`（ローカル画像生成診断実験。MEMORIELAのCanonや本番FREE仕様を更新する資料ではない）  
確認日: 2026-11-22 JST  
入口: \`START_HERE.md\` → \`docs/handoff/LOCAL_RAG_HANDOFF.md\` → 本書  
Git記録時のベース: \`main@e5fb3c1574e6a568be58b31b00655b4ae080bae9\`

## 0. この引き継ぎの目的・現在の評価

新チャットでは、2026-11-21〜22の試行から **成功した「衣装状態を保った再描画」の入力分離を再利用し、胸部・骨盤／鼠径部・下半身の描写密度、色白肌、マットなアニメ寄りレンダリングを改善する**。

最終目的は、ユーザーが指定する成人女性の顔・髪・体格・構図・衣装状態を維持し、GPT画像生成に近い品質のローカル生成を実現すること。**最終品質は未達**。ユーザーの判断を勝手に合格基準へ置き換えない。

直近の成功観測: ユーザーが \`redraw_role_separation_v1\` の生成画像を確認し「OK、衣装変更は問題なくできている」と判断。**当該1枚について衣装状態維持の目視実績あり**。異なるseed/ポーズ/入力での安定成功率、完全な人物同一性、解剖学的正確性、最終レンダリング品質の達成は未証明。

## 1. プロジェクト境界と保存上の注意

- Git: \`https://github.com/Pin-Gin/local-image-generator\`、ローカルルート: \`C:\Dev\local-image-generator\`。
- 既存の本番FREE、Outfit Delta v1、v8.2ポーズ、Render Refine、Redraw Identity、Body Form + Matte、Body Skin Styleは変更・削除・上書きしない。新しい診断は別ファイル／別出力フォルダで比較する。
- **重要:** 記録時のGit \`main\` はv8.2までのコードが主体。2026-11-21〜22に配布・Windowsへ導入されたFLUX3比較／Outfit Delta／Redraw系追加スクリプトの多くはGit未追跡。**本書をGitに追加しただけでは、別PCのクリーンcloneで同一生成を再現できない。** 次のコード保存時にはWindows実ファイルと差分・SHAを照合し、対象を選んでコミットする。
- 個人の参照画像・生成画像・モデル重み・LoRA・データセット・キャッシュは、明示承認なしにGitへ追加しない。\`git add .\` 禁止。
- これはMEMORIELAとは無関係の、オリジナル成人女性画像の独立実験。

## 2. 再開基準となる入力・ハッシュ

| 役割 | Windowsで使用したファイル | 確認済み事項 |
| --- | --- | --- |
| Master（人物と色味の基準） | \`$HOME\Downloads\outfit_master_verified.png\` | 941×1672、SHA256 \`e366e6c081b7a7bfb679148e50ccd3b5a6fb6d464770c9cb764a1408d4ba5325\` |
| Candidate（身体・構図・衣装状態の基準） | \`$HOME\Downloads\outfit_delta_unverified (1).png\` | SHA256 \`af4a958193c0959669dd09ffa68a079ce834c874628e4c507623a1918de14843\`（過去実験記録。実行時に再検証） |
| 直近の成功確認画像 | Windowsの \`LOCAL_RAG_REDRAW_ROLES_V1_00001_.png\` | ユーザーの添付コピー768×1360、SHA256 \`3f2026c3050fb58b5fded7df9cb689cfcaf0ac626bf9a91086a4c8fed97e1f1a\`。**添付コピーについてのSHA** |
| 直前に衣装が復活した比較失敗画像 | \`LOCAL_RAG_BODY_SKIN_STYLE_V1_00001_.png\` | 添付コピー768×1360、SHA256 \`d2f77fe8550aec5dad7f9790687f36bf819ca5ab1d4f1269850f1f3f67ac306e\` |

※アップロードされた画像のハッシュと、Windows側出力ファイルのハッシュが一致するかは未確認。再開時にはWindowsの実ファイルを優先し、上表の一致を確認する。

実験のBaseline参照: \`examples/render_refine_baseline_observed.json\`。肌色比較参照: \`examples/body_skin_style_v1_skin_patches.json\`。これらのローカル実ファイルと内容を必ず確認し、存在しない場合は勝手に代替値を作らない。

## 3. 何が失敗し、何が成功したか

| 系統 | 観測結果 | 次回の扱い |
| --- | --- | --- |
| Qwen Render Refine v1/v2 | 肌や胴体の形状情報量が十分に増えない | 既存結果を比較用に保存。無目的な追加調整を避ける |
| Qwen Raw Compare ROI | 上半身拡大でも描画密度不足 | 単純なROI拡大を最終解としない |
| FLUX3 Klein ROI Refine | 生出力に軽微な変化はあるが目標の描画密度に未達 | 比較Baseline |
| \`redraw_identity_v1\` FLUX3全画面再描画 | 全身・輪郭・立体感に一定の改善。画風と解剖表現は未完成 | 再描画能力の検証結果として維持 |
| \`redraw_body_form_matte_ab\` | 描画は変化したが、下半身の情報量不足と肌色の暖色化が残る | 比較Baseline |
| \`redraw_body_skin_style_v1\` | 元Masterのキャミソールとショートパンツが復活 | **衣装条件FAIL**、現在の成功経路として使用しない |
| **\`redraw_role_separation_v1\`** | Candidateの衣装状態を維持した生成画像をユーザーが目視確認 | **現行の再開ベースライン（衣装状態に限定した成功）** |

衣装復活の調査（旧オフライングラフ）では、\`ReferenceMultiLatent.images.image1\` に**衣装を含むMaster全身**を渡し、\`TextGenerate\` が双方の画像からプロンプトを書き直していた。衣装の再出現と整合するが、原因を厳密に個別切り分けた実験ではない。新しい成功例は「全身Masterの除外」と「Prompt Upsampler無効」を同時に実施した結果であり、単独の寄与は未分離。

## 4. 壊してはいけない成功構造

\`\`\`text
Candidate 全身（衣装状態・体格・姿勢・背景）
  -> ReferenceMultiLatent.images.image0

Master 全身
  -> ローカルの比較／肌色測定にだけ使用
  -> 顔・髪だけをクロップ
       -> ReferenceMultiLatent.images.image1

固定の役割指示（Prompt Upsampler / TextGenerate は使用しない）
  -> FLUX 3 Image Klein distilled INT8
  -> fresh latent / full-frame redraw
  -> raw_redraw.png
  -> 目視衣装状態チェック -> 身体描写・肌色・画風・人物同一性QA
\`\`\`

- Master全身を\`ReferenceMultiLatent\`へ直接入れない。人物参照の役割は顔・髪クロップに限定。
- 参照画像の物理的な切り出しが重要。文章で「衣装は無視」と書くだけでは入力画像から衣装情報が消えない。
- \`Reference 0\` はCandidate全身、\`Reference 1\` はMasterの顔・髪クロップ。クロップ範囲の正規化座標は **\`(0.295, 0.0, 0.675, 0.154)\`**、観測マスターでは約357×257px。今後の新マスターではクロップを目視承認し直す。
- 元Master全身の再アップロード、参照順の交換、Prompt Upsampler再投入、モデル変更、追加LoRA学習は別の実験として明示する。既存結果へ混入させない。
- モデル側に厳密な顔・姿勢・衣装拘束を保証する仕組みではない。ユーザーの目視QAを必須にする。

### 現在の再描画条件（配布した \`redraw_role_separation_v1\` コードで確認）

- diffusion model: \`flux3-image-klein-int8-convrot.safetensors\`
- text encoder: \`qwen3vl_4b_int8_convrot.safetensors\`
- VAE: \`flux2-vae.safetensors\`
- FLUX3 distilled: steps **16**、cfg **1**、denoise **1.0**、seed **975311**、fresh latent
- sampler: \`euler\`、scheduler: \`simple\`（旧比較グラフ基準）
- Prompt Upsampler: **OFF**。 \`qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors\` はこの成功経路の実行には使用しない。
- ComfyUI: \`http://127.0.0.1:8188\`。以前の\`ReferenceMultiLatent\`ノード不足はユーザーのComfyUI更新後に解消したが、再開時には現バージョンとノードを再確認。
- GPU: RTX 5080（16GB）、ローカルPython: \`.\tools\python312\python.exe\`。
- 参照画像1.0MP、出力サイズやモデル等の実行詳細は **Windows上で生成された当該回の \`request.json\` / \`workflow_api.json\` が最終証拠**。前回のZIP既定値だけで完全同一条件と断言しない。

### 実装と配布履歴

現行成功経路のスクリプト（Windowsに配布済み）:

\`\`\`text
experiments/active/redraw_role_separation_v1.py
experiments/active/reference_role_lock_v1.py
tests/unit/test_redraw_role_separation_v1.py
tests/unit/test_reference_role_lock_v1.py
docs/experiments/REDRAW_ROLE_SEPARATION_V1.md
\`\`\`

チャット配布ZIP: \`redraw_role_separation_v1_patch.zip\`、配布コピーSHA256 \`3a1760c763db9a44153b9f535e66626307e390609ed0ecae068758e4ac97e576\`。これは導入パッチであってGit上の追跡済みコードではない。新チャットで利用可能とは限らない。

依存実装として少なくとも\`flux3_klein_compare.py\`、\`redraw_identity_v1.py\`、\`lower_body_detail_v1.py\`、\`skin_tone_lock_v1.py\`、\`style_lock_v1.py\`、各関連のBaseline／QA設定ファイルがローカルに必要。**Gitだけではこれらが揃っていると推定しない**。

## 5. Windows再開手順（PowerShellは必ず1行ずつ）

まずローカルの実際のファイル、ブランチ状態、画像SHAを照合する。Gitが進んでいたら未コミットの既存変更を保持する。

\`\`\`powershell
Set-Location 'C:\Dev\local-image-generator'; git status -sb
\`\`\`

\`\`\`powershell
$master="$HOME\Downloads\outfit_master_verified.png"; $candidate="$HOME\Downloads\outfit_delta_unverified (1).png"; Get-FileHash -Algorithm SHA256 $master,$candidate
\`\`\`

\`\`\`powershell
@('test_reference_role_lock_v1.py','test_redraw_role_separation_v1.py') | ForEach-Object { .\tools\python312\python.exe -m unittest discover -s .\tests\unit -p $_ -v; if ($LASTEXITCODE -ne 0) { throw "TEST_FAILED: $_" } }
\`\`\`

**準備のみ（GPU生成なし）**

\`\`\`powershell
.\tools\python312\python.exe .\experiments\active\redraw_role_separation_v1.py --master $master --candidate $candidate
\`\`\`

出力ログの\`[REDRAW_ROLES:OUTPUT]\`にある \`master_head_hair_ref.png\` と \`reference_preview.png\` を確認し、クロップに衣装が含まれないことを目視確認。

**ComfyUI起動後のpreflight**

\`\`\`powershell
.\tools\python312\python.exe .\experiments\active\redraw_role_separation_v1.py --master $master --candidate $candidate --preflight
\`\`\`

**同じ条件で1枚生成（preflight PASS、クロップ承認後のみ）**

\`\`\`powershell
.\tools\python312\python.exe .\experiments\active\redraw_role_separation_v1.py --master $master --candidate $candidate --run --approve-run --approve-reference-crop
\`\`\`

※上の実行は再現条件確認用。新規チャットの最初に無条件で再生成する必要はない。前回の成功実行フォルダにある \`workflow_api.json\` / \`request.json\` / \`raw_redraw.png\` を優先して保全し、比較用途に使う。

## 6. 次に改善する対象と受け入れ判定

優先順位（ユーザー指定）:

1. **胸部・鼠径部・下半身の描写密度と解剖学的な形状連続性**。外陰部周辺の不自然な焼灼・極端な平滑化・描画欠落も確認する。これは非性的な造形・人体QA。
2. **マスター由来の色白肌への復帰／維持**。顔・首・胴体・脚の色相／明度／彩度の一貫性を別々に確認する。
3. **マットなアニメ／イラストらしさを維持しつつレンダリングの強化**。ユーザーは一定のリアル感増加を許容。画風の変化だけを自動FAILにしない。
4. 顔・髪型・体格・姿勢・背景など、指定外の変更を防ぐ。

可能なら1〜3を同時に改善するが、**衣装状態と人物同一性を犠牲にしない**。QA指標が改善しても目視で不足があれば不採用。

| 判定対象 | 採用条件 |
| --- | --- |
| 衣装状態 | Candidateで確定した状態を保持。旧衣装が復活したらFAIL |
| ボディ | 胸郭・骨盤／鼠径部・大腿・膝・下腿・足首の形と陰影が自然に明瞭 |
| 描画欠落 | 目視で不自然な局所平滑化・無情報化が確認されたらFAIL。画像処理指標単独では解剖学的正誤を断定しない |
| 色白肌 | Masterの可視肌を測色基準とし、顔と身体の大きな色ズレがない |
| 画風 | マットなアニメ系。鮮明さは増してもCGI/PBRや不必要な光沢は避ける |
| 人物同一性 | 顔・髪・体格・プロポーションが不意に変わらない |
| 構図 | 立位の全身・画角が勝手に変わらない |

### 推奨する次の実装／実験

既存の \`redraw_role_separation_v1\` をそのまま比較Baselineとして凍結し、**独立した新Variant／新スクリプト** から以下をA/B検証する。

- 姿勢・顔・衣装状態の参照役割を保持したまま、胴体・骨盤／脚の形状と陰影の描画密度を増やす。
- \`skin_tone_lock_v1.py\` のMaster測色結果を制約に使い、顔と身体の肌色の一貫性を診断する。
- \`lower_body_detail_v1.py\` のROI診断と目視レビューを組み合わせる。
- \`style_lock_v1.py\` は描画密度改善と不要な画風逸脱を分けて扱う。
- 一度に複数パラメータ／モデル／参照画像の役割を変えず、成功した変化だけを次へ継承する。
- 既存の「衣装復活失敗経路」へ戻って修正を重ねるのではなく、成功した参照分離経路から比較する。

## 7. 再開時に最初に調べること

1. \`START_HERE.md\`、\`LOCAL_RAG_HANDOFF.md\`、本書、現行\`main\`を実際に読む。Gitの正本より会話要約を優先しない。
2. Windowsの \`git status -sb\`、\`redraw_role_separation_v1.py\` と依存ファイルの存在・SHAを確認する。Gitの資料が最新でも、Windowsの未保存コードと生成物は別。
3. 前回成功回の \`request.json\` / \`workflow_api.json\` / \`reference_roles.json\` / \`manual_review_checklist_role.json\` / \`raw_redraw.png\` を実際に調べ、参照画像順、Prompt Upsampler OFF、model、seed、resolutionを確認する。ファイルがなければ未確認と報告する。
4. ユーザーの「衣装状態はOK」という評価を保持しつつ、胸部・鼠径部／下半身描画密度と肌色は未達のまま扱う。
5. 新規チャットで勝手にGitコード・本番FREE・人物設定を変更しない。変更が必要なら実際の差分とテストで説明する。

**再開用1文:** 「\`redraw_role_separation_v1\` で衣装状態の維持をユーザーが目視確認済み。全身Masterを参照入力に戻さず、Candidate全身＋Master顔髪クロップ、Prompt Upsampler OFFを維持したまま、胸部・鼠径部／下半身の描画密度と色白肌を優先し、可能ならマット系レンダリングも改善する。既存の成功経路は上書きしない。」
