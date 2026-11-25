"""CLI do pipeline. Uso: python -m stone_mpe.cli <comando> [opções]

  status                 estado de cada etapa (o que está pronto e o próximo comando)
  collect-youtube        coleta Shorts dos canais youtube do config/profiles.csv
  collect-instagram      Instagram via Apify (rota do kickoff), com estimativa e teto de custo
  import-instagram FILE  importa um export do Instagram (CSV/JSON/JSONL)
  build-base             normaliza, filtra ≥14 dias, calcula métrica e top 10%
  categorize             categoriza o top (--level 1|2, --rest-sample N) com checkpoint
  collect-comments       comentários dos Shorts do top (intenção de contato, dúvidas, objeções)
  import-comments FILE   comentários do Instagram exportados pela rota do kickoff
  precompute-demo        salva respostas da demo para o modo offline
  sample                 gera validation/manual_sample.csv (amostra cega ≥50)
  agreement              compara amostra manual × modelo (concordância, kappa, MAE)
  analyze                frequências, tema×formato, perfis em destaque
  ask MODE QUERY         executa o agente (analisar | recomendar | gerar_criativo)
  playbook               gera outputs/playbook.md
"""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="stone-mpe")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="mostra o estado de cada etapa do pipeline")
    sub.add_parser("collect-youtube")
    p = sub.add_parser("collect-instagram", help="Instagram via Apify (rota do kickoff); mostra o custo antes")
    p.add_argument("--posts", type=int, help="posts por perfil (padrão: settings.yaml)")
    p.add_argument("--max-usd", type=float, help="teto de gasto da execução")
    p.add_argument("--dry-run", action="store_true", help="só estima custo e mostra créditos, sem coletar")
    p = sub.add_parser("import-instagram")
    p.add_argument("file")
    p.add_argument("--route", required=True, help="nome da rota definida no kickoff (vai para source_route)")
    p.add_argument("--collected-at", help="data da coleta ISO, se o arquivo não tiver")
    sub.add_parser("build-base")
    p = sub.add_parser("categorize")
    p.add_argument("--limit", type=int)
    p.add_argument("--level", type=int, choices=[1, 2], default=1, help="2 = frames + transcrição (só vídeos)")
    p.add_argument("--rest-sample", type=int, default=0, help="categoriza N posts FORA do top (comparação top × resto)")
    p.add_argument("--until-done", action="store_true", help="se todos os provedores falharem, espera e retoma sozinho")
    p.add_argument("--wait", type=float, default=180, help="segundos de espera entre rodadas (--until-done)")
    p.add_argument("--max-hours", type=float, default=6)
    sub.add_parser("collect-comments")
    p = sub.add_parser("import-comments")
    p.add_argument("file")
    sub.add_parser("precompute-demo")
    p = sub.add_parser("pipeline", help="coleta YT → base → categorização N1 → comentários → análise → playbook → cache da demo")
    p.add_argument("--skip-collect", action="store_true")
    p.add_argument("--rest-sample", type=int, default=150)
    p = sub.add_parser("sample")
    p.add_argument("-n", type=int, default=50)
    p.add_argument("--overwrite", action="store_true", help="sorteia de novo mesmo se já houver rótulos")
    sub.add_parser("agreement")
    p = sub.add_parser("cross-check", help="concordância entre modelos na amostra (complementar à validação humana)")
    p.add_argument("--model", default="gemma-4-26b-a4b-it,gemma-4-31b-it", help="verificador(es), em ordem")
    sub.add_parser("analyze")
    sub.add_parser("weighted", help="Índice de Desempenho Ponderado: top por nicho, perfil, período e porte")
    sub.add_parser("export-release", help="exporta a base pública sanitizada para data/release/")
    p = sub.add_parser("bootstrap", help="monta o banco local a partir de data/release/ (clone novo)")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("ask")
    p.add_argument("mode", choices=["analisar", "recomendar", "gerar_criativo"])
    p.add_argument("query")
    p.add_argument("--segment")
    p.add_argument("--platform", choices=["instagram", "youtube"])
    p.add_argument("--profile-size", choices=["micro", "medio", "grande"])
    p.add_argument("--tipo-post", choices=["reels", "carrossel", "imagem", "short"])
    p.add_argument("-n", type=int, default=1)
    sub.add_parser("playbook")
    a = ap.parse_args(argv)

    if a.cmd == "status":
        from stone_mpe import status
        icon = {"ok": "[ok]", "parcial": "[..]", "pendente": "[  ]"}
        for r in status.pipeline():
            print(f"{icon[r['status']]} {r['etapa']:<22} {r['numero']:>6}  {r['detalhe']}")
            if r["status"] != "ok":
                print(f"{'':28}-> {r['comando']}")
    elif a.cmd == "collect-youtube":
        from stone_mpe import config
        from stone_mpe.collect import youtube
        prof = pd.read_csv(config.path("config", "profiles.csv"), dtype=str)
        handles = prof.loc[prof.platform == "youtube", "handle"].tolist()
        total, meter, fails = youtube.collect_many(handles)
        print(json.dumps({"shorts": total, "quota_units": meter.total, "falhas": fails}, ensure_ascii=False, indent=2))
    elif a.cmd == "collect-instagram":
        from stone_mpe.collect import apify
        print(json.dumps({"conta_apify": apify.account()}, ensure_ascii=False))
        print(json.dumps(apify.collect(posts_per_profile=a.posts, max_charge_usd=a.max_usd, dry_run=a.dry_run),
                         ensure_ascii=False, indent=2))
    elif a.cmd == "import-instagram":
        from stone_mpe.collect import instagram
        n, errs = instagram.import_file(a.file, a.route, a.collected_at)
        print(f"{n} posts importados; {len(errs)} erros")
        for e in errs[:20]:
            print("  ", e)
    elif a.cmd == "build-base":
        from stone_mpe.process import normalize
        print(json.dumps(normalize.run(), ensure_ascii=False, indent=2, default=str))
    elif a.cmd == "categorize":
        from stone_mpe.multimodal import categorize
        if a.until_done:
            res = categorize.run_until_done(level=a.level, rest_sample=a.rest_sample, wait_s=a.wait, max_hours=a.max_hours)
        else:
            res = categorize.run(limit=a.limit, level=a.level, rest_sample=a.rest_sample)
        print(json.dumps(res, indent=2))
    elif a.cmd == "collect-comments":
        from stone_mpe.analysis import comments
        print(json.dumps(comments.collect_youtube_top(), indent=2))
    elif a.cmd == "import-comments":
        from stone_mpe.analysis import comments
        print(json.dumps(comments.import_file(a.file), indent=2))
    elif a.cmd == "pipeline":
        from stone_mpe import config as _cfg
        collect = [["collect-youtube"]] + ([["collect-instagram"]] if _cfg.env("APIFY_TOKEN") else [])
        steps = ([] if a.skip_collect else collect) + [
            ["build-base"], ["categorize", "--until-done"], ["categorize", "--rest-sample", str(a.rest_sample), "--until-done"],
            ["collect-comments"], ["analyze"], ["playbook"], ["precompute-demo"]]
        for st_ in steps:
            print(f"\n===== {' '.join(st_)} =====", flush=True)
            try:
                main(st_)
            except Exception as e:  # registra e segue: etapas posteriores usam o que houver
                print(f"[pipeline] etapa '{st_[0]}' falhou: {e}")
    elif a.cmd == "precompute-demo":
        from stone_mpe import demo_cache
        print(f"{demo_cache.precompute()} respostas em {demo_cache.path()}")
    elif a.cmd == "sample":
        from stone_mpe.analysis import agreement
        s = agreement.make_sample(a.n, overwrite=a.overwrite)
        print(f"{len(s)} posts em {agreement.sample_path()}. Rotule com: streamlit run demo/rotular.py")
    elif a.cmd == "agreement":
        from stone_mpe.analysis import agreement
        print(agreement.compute().to_string(index=False))
    elif a.cmd == "cross-check":
        from stone_mpe.analysis import agreement
        print(agreement.cross_model(a.model).to_string(index=False))
    elif a.cmd == "analyze":
        from stone_mpe import config
        from stone_mpe.analysis import comments, creators, lead_signals, patterns
        summary = patterns.report()
        top = patterns.load_top()
        feat = creators.featured(top)
        feat.to_csv(config.outputs_dir() / "perfis_destaque.csv", index=False)
        summary["lead"] = lead_signals.cta_summary(top)
        summary["comentarios"] = {k: v for k, v in comments.summary().items() if k != "exemplos"}
        lf = patterns.lift()
        if not lf.empty:
            lf.drop(columns=["example_post_ids"]).to_csv(config.outputs_dir() / "lift_top_vs_resto.csv", index=False)
            summary["lift_top5"] = lf.head(5)[["field", "value", "lift"]].round(2).to_dict(orient="records")
        from stone_mpe.analysis import weighted
        summary["indice_ponderado"] = weighted.save()
        summary["perfis_destaque_top5"] = feat.head(5)[["handle", "platform", "n_top", "tema_predominante"]].to_dict(orient="records") if not feat.empty else []
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    elif a.cmd == "weighted":
        from stone_mpe.analysis import weighted
        print(json.dumps(weighted.save(), ensure_ascii=False, indent=2))
    elif a.cmd == "export-release":
        from stone_mpe import release
        print(json.dumps(release.export(), ensure_ascii=False, indent=2))
    elif a.cmd == "bootstrap":
        from stone_mpe import release
        print(json.dumps(release.restore(force=a.force), ensure_ascii=False, indent=2))
    elif a.cmd == "ask":
        from stone_mpe.api import run
        filters = {k: v for k, v in dict(platform=a.platform, profile_size=a.profile_size, tipo_post=a.tipo_post).items() if v}
        out = run(a.mode, a.query, segment=a.segment, filters=filters or None, n_creatives=a.n)
        print(out.model_dump_json(indent=2))
    elif a.cmd == "playbook":
        from stone_mpe import config, playbook
        playbook.build()
        print(f"playbook gerado em {config.outputs_dir() / 'playbook.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
