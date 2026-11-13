#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automacao para baixar lista de imoveis da Caixa Economica Federal - Estado do RJ
"""

import asyncio
import os
import sys
import unicodedata
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


DOWNLOAD_DIR = Path("./downloads/caixa")
URL = "https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp"


async def main():
    # Criar diretorio de download
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Diretorio de download: {DOWNLOAD_DIR.absolute()}")

    async with async_playwright() as p:
        # Iniciar Chromium
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            # User agent mais realista
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Configurar timeout padrao
        page.set_default_timeout(60000)

        try:
            print(f"Acessando: {URL}")
            await page.goto(URL, wait_until="networkidle")
            print("Pagina carregada")

            # Aguardar um pouco para garantir que tudo carregou
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)

            # Tirar screenshot inicial para debug
            await page.screenshot(path=DOWNLOAD_DIR / "01_pagina_inicial.png")
            print("Screenshot inicial salvo")

            # Localizar o campo de selecao de Estado (UF)
            # Vamos inspecionar a pagina para encontrar o seletor correto
            print("Procurando campo de selecao de UF...")

            # Tentar diferentes seletores possiveis para o dropdown de UF
            uf_selectors = [
                'select[name*="uf" i]',
                'select[id*="uf" i]',
                'select[name*="estado" i]',
                'select[id*="estado" i]',
                'select.uf',
                '#uf',
                'select',
            ]

            uf_element = None
            for selector in uf_selectors:
                try:
                    uf_element = await page.wait_for_selector(selector, timeout=5000)
                    if uf_element:
                        print(f"Campo UF encontrado com seletor: {selector}")
                        break
                except PlaywrightTimeoutError:
                    continue

            if not uf_element:
                # Tentar encontrar todos os selects na pagina
                selects = await page.query_selector_all("select")
                print(f"Encontrados {len(selects)} elementos <select> na pagina")
                for i, sel in enumerate(selects):
                    name = await sel.get_attribute("name")
                    id_attr = await sel.get_attribute("id")
                    class_attr = await sel.get_attribute("class")
                    print(f"  Select {i}: name={name}, id={id_attr}, class={class_attr}")
                    # Verificar se tem opcoes de estados
                    options = await sel.query_selector_all("option")
                    option_texts = []
                    for opt in options[:5]:
                        text = await opt.inner_text()
                        option_texts.append(text.strip())
                    print(f"    Primeiras opcoes: {option_texts}")
                    if any("Rio" in opt or "RJ" in opt for opt in option_texts):
                        uf_element = sel
                        print(f"Campo UF identificado como select index {i}")
                        break

            if not uf_element:
                raise Exception("Nao foi possivel localizar o campo de selecao de UF")

            # Selecionar RJ - Rio de Janeiro
            print("Selecionando RJ - Rio de Janeiro...")
            try:
                # Tentar por value
                await uf_element.select_option(value="RJ")
                print("RJ selecionado por value")
            except Exception:
                try:
                    # Tentar por label
                    await uf_element.select_option(label="Rio de Janeiro")
                    print("RJ selecionado por label")
                except Exception:
                    try:
                        # Tentar por index (geralmente RJ e um dos primeiros)
                        await uf_element.select_option(index=19)  # RJ costuma ser ~19o
                        print("RJ selecionado por index")
                    except Exception as e:
                        # Listar todas as opcoes para debug
                        options = await uf_element.query_selector_all("option")
                        for i, opt in enumerate(options):
                            value = await opt.get_attribute("value")
                            text = await opt.inner_text()
                            print(f"  Option {i}: value={value}, text={text.strip()}")
                        raise Exception(f"Nao foi possivel selecionar RJ: {e}")

            await asyncio.sleep(1)

            # Tirar screenshot apos selecao
            await page.screenshot(path=DOWNLOAD_DIR / "02_apos_selecao_rj.png")
            print("Screenshot apos selecao RJ salvo")

            # Localizar e clicar no botao Proximo
            print("Procurando botao Proximo...")
            proximo_selectors = [
                '#btn_next1',
                'button[id="btn_next1"]',
                'button.submit-blue',
                'button.submit-d.submit-blue.submit-small',
                'input[type="submit"][value*="Proximo" i]',
                'button:has-text("Proximo")',
                'button:has-text("Próximo")',
                'input[value*="Proximo" i]',
                'a:has-text("Proximo")',
                'button[type="submit"]',
                'input[type="submit"]',
                '[onclick*="proximo" i]',
                '[onclick*="next" i]',
            ]

            proximo_clicked = False
            download = None
            for selector in proximo_selectors:
                try:
                    btn = await page.wait_for_selector(selector, timeout=3000)
                    if btn:
                        # Verificar se esta visivel e habilitado
                        is_visible = await btn.is_visible()
                        is_enabled = await btn.is_enabled()
                        print(f"  Botao encontrado: {selector} (visivel={is_visible}, habilitado={is_enabled})")
                        if is_visible and is_enabled:
                            # Tentar clicar e capturar download, mas lidar com navegacao
                            try:
                                async with page.expect_download(timeout=10000) as download_info:
                                    await btn.click()
                                download = await download_info.value
                                proximo_clicked = True
                                print("Botao Proximo clicado, download iniciado")
                                break
                            except PlaywrightTimeoutError:
                                # Click nao gerou download, pode ter navegado para pagina de validacao
                                print("  Click nao gerou download imediato, verificando se houve navegacao...")
                                await page.wait_for_load_state("networkidle")
                                await asyncio.sleep(2)
                                current_url = page.url
                                print(f"  URL apos click: {current_url}")

                                # Se caiu em pagina de validacao (perfdrive/radware), tentar URL direta
                                if "validate.perfdrive.com" in current_url or "radware" in current_url:
                                    print("  Detectada pagina de validacao anti-bot, voltando para pagina original...")
                                    # Voltar para a pagina original onde o formulario ja tem RJ selecionado
                                    await page.goto(URL, wait_until="networkidle")
                                    await asyncio.sleep(2)
                                    print("  De volta a pagina original, tentando clicar novamente...")
                                    # Encontrar o botao novamente e clicar
                                    try:
                                        btn = await page.wait_for_selector('#btn_next1', timeout=5000)
                                        if btn:
                                            is_visible = await btn.is_visible()
                                            is_enabled = await btn.is_enabled()
                                            if is_visible and is_enabled:
                                                async with page.expect_download(timeout=30000) as download_info:
                                                    await btn.click()
                                                download = await download_info.value
                                                proximo_clicked = True
                                                print("  Download iniciado na segunda tentativa")
                                                break
                                    except Exception as e:
                                        print(f"  Erro na segunda tentativa: {e}")

                                    # Se ainda falhou, tentar URL direta em uma nova pagina
                                    if download is None:
                                        print("  Tentando URL direta em nova pagina...")
                                        new_page = await context.new_page()
                                        try:
                                            async with new_page.expect_download(timeout=30000) as download_info:
                                                await new_page.goto("https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_RJ.csv", wait_until="commit")
                                            download = await download_info.value
                                            proximo_clicked = True
                                            print("  Download iniciado via nova pagina")
                                            break
                                        except Exception as e:
                                            print(f"  Erro na nova pagina: {e}")
                                            await new_page.close()
                                else:
                                    # Navegou para outra pagina, continuar tentando
                                    proximo_clicked = True
                                    print("  Navegou para outra pagina, continuando...")
                                    break
                except PlaywrightTimeoutError:
                    continue

            if not proximo_clicked:
                # Tentar encontrar todos os botoes/inputs de submit
                buttons = await page.query_selector_all('button, input[type="submit"], input[type="button"], a[href]')
                print(f"Encontrados {len(buttons)} botoes/links na pagina")
                for i, btn in enumerate(buttons):
                    tag = await btn.evaluate("el => el.tagName.toLowerCase()")
                    text = await btn.inner_text()
                    value = await btn.get_attribute("value")
                    onclick = await btn.get_attribute("onclick")
                    href = await btn.get_attribute("href")
                    class_attr = await btn.get_attribute("class")
                    id_attr = await btn.get_attribute("id")
                    print(f"  Botao {i}: tag={tag}, text='{text.strip()}', value='{value}', onclick='{onclick}', href='{href}', class='{class_attr}', id='{id_attr}'")
                    # Normalizar texto para comparacao (remover acentos)
                    text_norm = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII').lower()
                    value_norm = unicodedata.normalize('NFKD', value or '').encode('ASCII', 'ignore').decode('ASCII').lower()
                    if "proximo" in text_norm or "proximo" in value_norm:
                        print(f"  Tentando clicar no botao {i}...")
                        async with page.expect_download() as download_info:
                            await btn.click()
                        download = await download_info.value
                        proximo_clicked = True
                        print("Botao Proximo clicado via busca ampla")
                        break

            if not proximo_clicked:
                raise Exception("Nao foi possivel localizar ou clicar no botao Proximo")

            # Se ainda nao tem download, tentar URL direta
            if download is None:
                print("Tentando URL direta do download como fallback...")
                direct_download_url = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_RJ.csv"
                try:
                    async with page.expect_download(timeout=30000) as download_info:
                        await page.goto(direct_download_url, wait_until="commit")
                    download = await download_info.value
                    print("Download iniciado via URL direta (fallback)")
                except Exception as e:
                    if "Download is starting" in str(e):
                        print("  Download detectado (erro 'Download is starting' esperado)")
                        # O download foi capturado pelo expect_download apesar do erro
                        # Tentar obter o download do context
                        try:
                            # Aguardar um pouco para o download completar
                            await asyncio.sleep(3)
                            # Verificar arquivos no diretorio
                            downloaded_files = list(DOWNLOAD_DIR.glob("*.csv"))
                            if downloaded_files:
                                latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
                                print(f"  Arquivo encontrado: {latest_file.name}")
                                class MockDownload:
                                    def __init__(self, path):
                                        self._path = path
                                        self.suggested_filename = path.name
                                    async def save_as(self, dest):
                                        import shutil
                                        shutil.copy2(self._path, dest)
                                download = MockDownload(latest_file)
                            else:
                                raise Exception("Download nao encontrado no diretorio")
                        except Exception as e2:
                            print(f"  Erro ao verificar download: {e2}")
                            raise
                    else:
                        raise

            # Aguardar o download completar
            print("Aguardando download completar...")
            await download.save_as(DOWNLOAD_DIR / download.suggested_filename)
            print(f"Download concluido: {download.suggested_filename}")

            # Tirar screenshot final
            await page.screenshot(path=DOWNLOAD_DIR / "03_apos_download.png")
            print("Screenshot final salvo")

        except Exception as e:
            print(f"Erro durante a automação: {e}")
            # Capturar screenshot de erro
            await page.screenshot(path=DOWNLOAD_DIR / "erro.png")
            print("Screenshot de erro salvo")
            # Registrar URL atual
            current_url = page.url
            print(f"URL atual: {current_url}")
            # Salvar HTML para analise
            html_content = await page.content()
            with open(DOWNLOAD_DIR / "erro_pagina.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("HTML da pagina salvo para analise")
            await browser.close()
            return False

        await browser.close()

        # Validacao final do arquivo baixado
        downloaded_files = list(DOWNLOAD_DIR.glob("*"))
        # Filtrar apenas arquivos de download (nao screenshots/html)
        download_files = [f for f in downloaded_files if f.suffix not in [".png", ".html"] and f.name != "erro.png"]

        if not download_files:
            print("Nenhum arquivo de download encontrado")
            return False

        # Pegar o arquivo mais recente (o download)
        latest_file = max(download_files, key=lambda f: f.stat().st_mtime)
        file_size = latest_file.stat().st_size

        print("\n" + "="*60)
        print("VALIDACAO FINAL")
        print("="*60)
        print(f"Arquivo existe: {latest_file.name}")
        print(f"Caminho absoluto: {latest_file.absolute()}")
        print(f"Tamanho: {file_size} bytes ({file_size/1024:.2f} KB)")
        print(f"Extensao: {latest_file.suffix}")
        print(f"Tamanho > 0: {'SIM' if file_size > 0 else 'NAO'}")

        if file_size == 0:
            print("AVISO: Arquivo baixado tem tamanho zero!")
            return False

        # Tentar identificar o formato
        if latest_file.suffix.lower() in [".csv", ".txt"]:
            print("Formato: Texto/CSV")
        elif latest_file.suffix.lower() in [".xls", ".xlsx"]:
            print("Formato: Planilha Excel")
        elif latest_file.suffix.lower() == ".pdf":
            print("Formato: PDF")
        elif latest_file.suffix.lower() == ".zip":
            print("Formato: Arquivo compactado ZIP")
        else:
            print(f"Formato desconhecido: {latest_file.suffix}")

        print("="*60)
        print("DOWNLOAD REALIZADO COM SUCESSO!")
        print("="*60)

        return True


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)