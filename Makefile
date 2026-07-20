.PHONY: figures benchmark

figures:
	@echo "Regenerating manuscript figures from final results..."
	Rscript scripts/make_submission_figures_r.R
	@echo "Figures regenerated in manuscript/figures/"

benchmark:
	@echo "Running computational latency benchmark..."
	python scripts/benchmark_nfsqi_latency.py --config configs/nfsqi_smr_central.yaml --n-windows 1000
