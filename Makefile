.PHONY: paper verify clean
paper:
	cd paper && latexmk -pdf -interaction=nonstopmode manuscript.tex
verify:
	cd release && sha256sum -c SHA256SUMS.txt --ignore-missing
clean:
	cd paper && latexmk -C manuscript.tex
