.PHONY: install data run sample test

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

data:            ## download real data + build data/eco2mix_daily.csv.gz (once)
	python scripts/fetch_data.py

sample:          ## synthetic offline data (clearly flagged in the app)
	ECO2MIX_SAMPLE=1 python scripts/fetch_data.py --sample

run:
	streamlit run app.py

test:
	ECO2MIX_SAMPLE=1 python -c "from streamlit.testing.v1 import AppTest; at=AppTest.from_file('app.py', default_timeout=240).run(); assert not at.exception, at.exception; print('OK')"
