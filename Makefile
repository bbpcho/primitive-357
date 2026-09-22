.PHONY: paper verify verify-release clean
paper:
	cd paper && latexmk -pdf -interaction=nonstopmode manuscript.tex
verify:
	cd release && sha256sum -c SHA256SUMS.txt --ignore-missing
verify-release:
	scripts/verify_release.sh
clean:
	cd paper && latexmk -C manuscript.tex
