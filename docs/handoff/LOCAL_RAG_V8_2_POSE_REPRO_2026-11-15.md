# 2026-11-15 v8.2 マネキン参照ポーズ生成：実績・再現手順

Status: **EXPERIMENT / USER-VISUALLY PROMISING / NOT ACCEPTED**
対象: local-image-generator（local-RAG）の実験系。MEMORIELA正史やFREE本番仕様の変更ではない。
最終更新: 2026-11-15（JST）
入口: START_HERE.md → docs/handoff/LOCAL_RAG_HANDOFF.md → 本ファイル

## 0. この文書の目的・判定範囲

2026-11-15の成人女性マスター1枚・日本語自然文・外部マネキンによるポーズ変更の試行から、**最も良好だったv8.2の経路を次回同じ条件で再開できるように記録する**。改善案を正史化・本番化しない。

ユーザーの最終目視評価: v8.2は「良いかも？」。これ以前のv8.1も「今日の中で一番近い」。v8.2では左右の足先が画面内、脚交差なし、手の接地、機械パーツ混入なしを視認できた。顔・短パンの形状・厳密なM字条件はなお未達／未確定である。

**品質の合格宣言ではない。** 同一人物85%以上、レンダリング100%、7.3頭身の正確性、全ポーズでの安定性は実証されていない。v8.2は再開基準（baseline）である。

## 1. Gitの正本とローカル資産の差（最重要）

この記録作成時、GitHubのmainは af5a56113978b11dfec4389acfa82c9e9dd61f10（2026-10-12）。GitHubの experiments/active/ には旧 free_ipadapter_pose_json_experiment.py のみがあり、**v7〜v8.2スクリプトは現行mainに含まれない**。

本資料をGitに保存しても、ローカルWindowsの未追跡実験コード、生成画像、モデル重み、ComfyUI入力画像や出力JSONは自動保存されない。**コードを含む完全再実行は、Windowsで使った実ファイルをGitへ別途保存するまで保証できない。** チャットで配布したZIPだけを永久保存場所として扱わない。

ローカル作業ツリーを勝手に削除・上書きしないこと。models/、learning/、database/、outputs/、tools/、LoRA、既存の画像・キャッシュを保護する。Gitへの新規追加は追跡対象を選んで実施する（セクション9）。

## 2. 成果の要点：なぜv8.2が現状の最良候補か

| 段階 | 観察結果 | 継承／不採用 |
| --- | --- | --- |
| v1〜v2 SDXL + IP-Adapter / OpenPose | 顔・髪・画風が別人化。IP-Adapter重み増加は画像崩壊を招く場合がある | この重み調整路線は不採用 |
| v3 SDXL + 頭部Inpaint | Stage 2で顔が髪で覆われ破綻 | 頭部の全面再生成を不採用 |
| v4〜v5 FLUX.2 Klein参照編集 | 衣装や背景の近さは改善したが、顔やM字座位が不一致 | この実験では不採用 |
| v6 Qwen-Image-Edit-2511（マスター＋骨格＋顔） | 長袖の別衣装など外観ドリフト | 参照画像を渡すだけでは固定できない |
| v7 SDXL仮画像 → Qwen復元 | 一部の顔・衣装・画風が改善。ただし脚交差、さらにマネキン追加後のSDXL Stage 1は解剖図状に破綻 | 2段階のSDXL仮人物生成を停止 |
| v8 QwenへマネキンRGBを直接入力 | 機械的な腕・肩・脚が人物へ混入し、胡坐になる | **マネキンRGBを最終モデルへ渡さない** |
| v8.1 マスター＋OpenPose＋マスター由来の顔／衣装 | 機械化が視認されず人物外観も接近。ただし足先が画面外、短パン形状は変化 | 人物参照・RGB遮断を維持 |
| **v8.2** v8.1＋縦長フレーム整合・頭頂／足先アンカー | **両足先が画面内に入り、脚交差なし、マネキンの座位に近づく**。顔／画風も比較的近いが衣装下部などは違う | **次回再開ベースライン** |

失敗の「原因」は接続・入力構造との関連が強い候補であり、個別要素の厳密な因果実験を全件実施したものではない。v8.2が最良という評価も提供画像に対する相対評価であり、成功率ではない。

## 3. 入力・前提・モデル条件

- 人物マスター: 正面立位、**941×1672 px**。成人女性、短いブラウン系ボブ、淡色キャミソール＋ショートパンツ、柔らかなマット系アニメ描写。今回の実験で確認する画風は Matte Soft Anime Realism。別系統の既存FREE標準 Matte Dimensional Anime と混同しない。
- マネキン参照: **1218×1292 px**、前向き床座り・左右開脚・両手後方支持。画像のSHA256は **26b09627f98adab1143e67d91850da1d0a226f1c2a9c2e6a8df7c421aa408c8d**。
- 元の指示文: **成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる**。
- 警告: マネキン上の左右足首は膝より**外側**。初期の「足首は膝より内側」という文章仕様と異なる。座位・脚非交差の再現と、元文章のM字定義への適合は別々に判定する。JSONを自動で辻褄合わせしない。
- 2D Pose: examples/mannequin_m_seated.pose.json（BODY_18、画像からの目視推定）。鼻位置は頭部中心の代理値、股関節は隠れた部分の推定。**3Dリグの計測値ではない**。
- 足先・頭頂: examples/mannequin_m_seated.frame.json（2D推定、元画像SHAに紐付く）。足先はBODY_18関節として挿入しない。
- ComfyUI: ユーザーWindowsで起動する API http://127.0.0.1:8188。現行バージョン・空きVRAM・モデル配置は再開時に再確認する。2026-10ハンドオフの環境値を今回の実測値と取り違えない。
- Qwenモデル（v8.2既定コード値）: qwen_image_edit_2511_int8_convrot.safetensors
- text encoder: qwen_2.5_vl_7b_fp8_scaled.safetensors
- VAE: qwen_image_vae.safetensors
- sampling: seed=975311、steps=20、cfg=4.0。画角以外の参照条件・サンプラーを変えずに比較。
- 外部マネキン→Pose JSON、OpenPose変換は内部機能を利用。ユーザーが毎回手作業で複数の資料を作ることは**最終製品の要件ではない**。今回の手順は検証実験用。

## 4. 再現の中核となる生成フロー

~~~text
MASTER 941x1672
 ├─ Qwen Image 1: 人物・衣装・描画の元マスター
 └─ 顔／髪・衣装の参照シート（マスターから抽出）
      └─ Qwen Image 3: 外観補助

3D風マネキン（解析にだけ使用。RGBを最終Qwenへ送らない）
 └─ 対応する画像SHAとBODY_18推定座標を検証
    ├─ Pose JSON / confidence / unknown 3D depth / contact warnings
    ├─ 頭頂・足先の2Dアンカー（画角チェック専用）
    └─ 座標から OpenPose RGB 768x1344 を描画
         └─ Qwen Image 2: POSE-ONLY参照画像

Image 1 + Image 2 + Image 3 + 日本語指示
 -> Qwen-Image-Edit-2511（SDXL仮人物段階なし）
 -> 生成画像・comparison.png・diagnostic.json
 -> 作者による外観／脚配置／足先／衣装／画風の個別QA
~~~

**注意**: Qwen Image 2はTextEncodeQwenImageEditPlusの画像参照であり、互換性確認済みのControlNet式「ハード関節固定」ではない。現状の判定は POSE_CONTROL_REFERENCE_ONLY。通常の厳格モードは停止し、検証時だけ --allow-reference-only を明示して実行する。

- マネキンRGBそのものを Image 2 に渡すと、過去に金属関節・手足の混入が見られたため禁止。
- silhouette／接地推定は診断データ。現在のv8.2では「シルエットをQwenへ独立制御入力として送信している」と主張しない。
- OpenPoseガイドのフレーム内余白が正しくても、Qwenが足先を描くとは限らない。必ず生成後に実画像で判定する。

## 5. v8.2で追加された画角調整

- 元のガイドは896×960（ほぼ正方形）。マスター941×1672と画面比率が大きく異なり、v8.1結果では足先が画面外へ出た。
- v8.2は**マスター縦横比**に合わせてOpenPoseガイドを**768×1344**に再投影し、頭頂・足先アンカーを余白検査へ使う。
- 関節は一様なスケールで投影し、身体部位ごとの長さを引き伸ばさない。元のBODY_18座標は改変しない。
- 開発オフライン確認では投影された関節と頭頂・足先の推定点が外枠から最小約69px離れる結果を確認。これは**画像出力の足先可視性を保証しない**。
- 出力の画角比と、人体各部が見えるかを別々のQAとする。

## 6. 必要なローカルファイル（Git mainには未収録）

~~~text
experiments/active/v8_pipeline.py
experiments/active/v8_direct_pose_edit.py
experiments/active/v8_frame_control.py
experiments/active/v8_pose_structure.py
experiments/active/v8_conditioning.py
experiments/active/v7_references.py
experiments/active/v7_geometry.py
experiments/active/v7_quality.py
experiments/active/qwen2511_reference_pose_v6.py
src/comfyui_client.py
examples/mannequin_m_seated.png                     # private pose reference; do not upload by default
examples/mannequin_m_seated.pose.json               # estimated 2D and source SHA
examples/mannequin_m_seated.frame.json              # estimated 2D head/toe anchors
outputs/experiments/text_pose_web/<session>/compiled_workflow.json  # --source mode only
~~~

ZIPの導入順（全て差分パッチ、単体では完全なv8.2環境にならない）:
1. qwen_v6_patch.zip（既に導入されている場合はハッシュとコードを確認し再インストール不要）
2. v7_architecture_patch_installer_fixed.zip
3. v7_external_pose_patch.zip
4. v8_direct_pose_patch.zip
5. v8_1_structure_patch.zip
6. v8_2_frame_patch.zip

厳密な復元時にはREADMEとインストーラーの前提SHAを確認し、既存ファイルに差分があれば**上書きせず**止める。ユーザーのWindows上の実コードを優先し、ZIPや過去会話は正本と見なさない。

v8.2配布ZIP SHA256（現チャットの生成物）:
b24060374e0b59a2b8c389f1319f46ca0a15352490ce7c29b131f79099f55338

実験時の主要スクリプトSHA256（配布版の検証用識別子、Windows実ファイルのハッシュ一致は未確認）:
- v8_pipeline.py: 26a398a242aca8839b2cf37165d74ad39e53ee694f844685fc9d022a1309a735
- v8_direct_pose_edit.py: d231188d1ea60d5f2c50cda6e11ee8859d163bd47c4f82263912a0a4fecaec64
- v8_frame_control.py: 7732ac4bf62c730a7e7ba18c4395f657f216c046c5bb86e98b9c09517b291399

## 7. Windowsでの再現手順（全コマンド1行、PowerShell 5.1対応）

**複数行のPowerShell行継続記号を使用しないこと。** 過去にコピー時の順序崩れが起きている。

起動条件: モデルとComfyUIが用意され、ローカルにセクション6のコード・画像・JSONが存在すること。ローカルの既存変更を守り、まず現在地を確認する。

~~~powershell
Set-Location "C:\Dev\local-image-generator"
~~~

~~~powershell
git status --short
~~~

~~~powershell
git rev-parse HEAD
~~~

~~~powershell
.\tools\python312\python.exe -m unittest discover -s .\tests\unit -p "test_v8_*.py" -v
~~~

開発用オフライン検証では v8系38件＋v7系25件の計63件PASS。ユーザーWindowsでの全テストPASSをこの資料が証明するものではない。

ローカルに旧セッションのcompiled_workflow.jsonとComfyUI側のマスターアップロードが残る場合:

~~~powershell
$source = "C:\Dev\local-image-generator\outputs\experiments\text_pose_web\20261115T055422_a000cbe4a055e0ad\compiled_workflow.json"
~~~

~~~powershell
$text = "成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる"
~~~

モデル／ノードを確認してガイドを生成（**GPU生成なし**）:

~~~powershell
.\tools\python312\python.exe .\experiments\active\v8_pipeline.py --source $source --text $text --pose-image ".\examples\mannequin_m_seated.png" --pose-json ".\examples\mannequin_m_seated.pose.json" --frame-anchors ".\examples\mannequin_m_seated.frame.json" --preflight --allow-reference-only
~~~

出力フォルダ（プログラムの表示を正とする）:

~~~text
outputs/experiments/v8_1_structure/<UTC timestamp>/
  geometry/external_openpose_fullframe.png
  geometry/frame_landmarks_review.png
  geometry/frame_alignment_v8_2.json
  reference_bundle/
  v8_1_api.json
  diagnostic.json
~~~

入力画像・JSONのSHA、関節と足先の位置、警告、Qwen画像入力3系統、人物外観ソースがMASTERのみであることを確認。必要ならここで終了する。

**レビュー後に試験画像1枚を生成**（厳密なポーズ拘束の保証なし、警告を明示受容）:

~~~powershell
.\tools\python312\python.exe .\experiments\active\v8_pipeline.py --source $source --text $text --pose-image ".\examples\mannequin_m_seated.png" --pose-json ".\examples\mannequin_m_seated.pose.json" --frame-anchors ".\examples\mannequin_m_seated.frame.json" --preflight --allow-reference-only --approve-unreviewed-pose --run
~~~

--sourceが存在しない場合、別の適当なcompiled_workflow.jsonを代用しない。v8_pipeline.pyの--masterオプションを使用して**実在する正しいマスター画像パス**を指定する。マスター画像の一致はSHAと目視で検証。未知のローカルファイルパスは作り上げない。

期待する実行状態: GENERATED_UNVERIFIED_REFERENCE_ONLY。これが示すのは「候補画像を生成した」であり、合格ではない。

## 8. 出力QAと記録方法

比較元マスターと生成画像を並べ、次を独立して記録する。

| 項目 | v8.2で観察した結果 | 次回合格判定の条件 |
| --- | --- | --- |
| 両足先 | 表示された | 両方の足首・足指が画面内で自然に識別可能 |
| 脚の交差 | 表示画像では交差なし | 交差・胡坐・蝶々座りへの置換なし |
| 膝と足首 | マネキンの配置に接近 | マネキンPose JSONに対して左右・相対位置を照合（元文章との差も別記） |
| 手・接地 | 後方に手をついた座位 | 手指や腕の欠損・機械化なし。接地の3D確定は未了 |
| 顔と髪 | 視覚的に以前より近い | マスターの目元、顔輪郭、髪長・毛束・色が一致 |
| 衣装 | 上半身比較的近い、短パン形状に差 | キャミソールとショートパンツの構造・色・材質が維持 |
| レンダリング | マット系の近さが見られた | 元のMatte Soft Anime Realismを崩さない |
| 背景 | 同種の部屋を維持する傾向 | 指示のない家具・小物の追加／変更をチェック |
| 頭身7.3 | 座位単独では定量検証不能 | 別の幾何資料や信頼できる測定で判定 |
| 同一人物85%・画風100% | **未証明** | 作者の目視と事前定義した比較基準で承認後のみ採用 |

一度の目視良好例を安定成功率へ換算しない。画像生成後は diagnostic.json、Pose JSON、使用モデル・シード、比較画像、作者のPASS/FAILを残す。ローカル出力画像と個人参照画像は許可なく公開Gitへアップロードしない。

## 9. Git保存を完成させるための残作業

この文書のGitコミットは**実験手順書の保存**である。現在のGitHub mainには実行コードが含まれず、Gitだけで完全な再現はまだできない。

次回または現PC上で、作者の確認のもと以下を実施する必要がある:
1. Windowsの現行v8.2コードと本書のファイルハッシュ・入出力を比較し、実験の正本スナップショットを特定する。
2. 現行コード（必要な依存スクリプト、該当テスト、JSON fixture）を追跡対象として追加する。未追跡の他の生成物や学習キャッシュを一括追加しない。
3. 参照画像をGitに含めるかを作者が判断する。公開が不要ならローカル保管とSHAで対応する。
4. コードがGitに保存されたら本書の依存／コミットSHAを更新し、清潔な作業環境での再実行まで確認する。

必要ファイルだけを選ぶため、**git add . は禁止**。モデル・素材・出力・個人の画像の誤投入を防ぐ。

## 10. 再開時の最初の判断

- まず START_HERE.md とLOCAL_RAG_HANDOFF.mdを確認。Gitの最新内容を優先。
- 本書v8.2の入力・モデル・三系統Image条件付けを照合。勝手に別モデルやポーズへ差し替えない。
- ユーザーが求める姿勢が今回のマネキンと異なる場合、新しいマネキン＋対応するPose JSON／フレームアンカーに更新し、SHA・推定値を明示。
- Stage 1のSDXL仮人物生成、マネキンRGB直接入力、高denoise頭部再生成には自動的に戻さない。
- フレームと足先が入るかを先に検証し、次にポーズ相対配置、その後に顔・衣装・画風を評価。
- 実験結果が崩れた場合は最初に差分（入力・画像SHA・コード・モデル・seed・画角）を確認。根拠なくWeightだけを再調整しない。

**保存済みの結論:** v8.2は2026-11-15時点で最も良い視覚的成果の再開基準。ただし最低条件をすべて満たした完成版ではない。
