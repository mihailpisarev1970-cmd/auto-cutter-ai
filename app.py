import os
import gradio as gr
from config import (
    get_default_desktop_dir,
    get_default_desktop_path,
    DEFAULT_LLM_MODEL,
    LLM_CHOICES,
)
from utils import open_folder_dialog
from downloader import download_or_cut_stream
from video_processor import convert_16_9_to_9_16
from ai_pipeline import process_video_pipeline

sand_theme = gr.themes.Soft(
    primary_hue=gr.themes.colors.amber,
    secondary_hue=gr.themes.colors.stone,
)

custom_css = """
.main-title {
    margin-top: 18px !important;
    margin-bottom: 8px !important;
}

#custom-nav-tabs {
    margin-top: 16px !important;
}

#custom-nav-tabs > div:first-child,
#custom-nav-tabs div[role="tablist"],
#custom-nav-tabs .tab-nav {
    display: flex !important;
    gap: 32px !important;
    background-color: #f7f5f2 !important;
    border-top: 1px solid #e7e5e4 !important;
    border-bottom: 4px solid #1e293b !important;
    padding: 14px 28px 0px 28px !important;
    margin-bottom: 24px !important;
    align-items: center !important;
    border-radius: 0 !important;
}

#custom-nav-tabs button[role="tab"],
#custom-nav-tabs .tab-nav > button {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    font-size: 1.08rem !important;
    font-weight: 500 !important;
    color: #2c3e50 !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 4px solid transparent !important;
    border-radius: 0 !important;
    padding: 6px 6px 14px 6px !important;
    margin-bottom: -4px !important;
    cursor: pointer !important;
    box-shadow: none !important;
    transition: color 0.15s ease, border-color 0.15s ease !important;
}

#custom-nav-tabs button[role="tab"] *,
#custom-nav-tabs .tab-nav > button * {
    color: inherit !important;
}

#custom-nav-tabs button[role="tab"]:hover,
#custom-nav-tabs .tab-nav > button:hover {
    color: #0f172a !important;
    background: transparent !important;
    border-bottom: 4px solid #94a3b8 !important;
}

#custom-nav-tabs button[role="tab"][aria-selected="true"],
#custom-nav-tabs button[role="tab"].selected,
#custom-nav-tabs .tab-nav > button.selected {
    color: #0f172a !important;
    font-weight: 700 !important;
    border-bottom: 4px solid #1e293b !important;
}

.browse-btn {
    margin-top: 24px !important;
}

.styled-label-badge {
    display: inline-block !important;
    background-color: #fef3c7 !important;
    color: #b45309 !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    padding: 3px 10px !important;
    border-radius: 6px !important;
    margin-top: 6px !important;
    margin-bottom: 4px !important;
}

.model-badge-container {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    height: 100% !important;
    margin-top: 4px !important;
}
"""

with gr.Blocks(title="Auto Cutter AI", theme=sand_theme, css=custom_css) as demo:
    gr.Markdown("## 🎬 Умный видеокомбайн", elem_classes=["main-title"])

    with gr.Tabs(elem_id="custom-nav-tabs"):
        # 1. ВКЛАДКА: СКАЧИВАНИЕ
        with gr.TabItem("⚡ Скачивание и быстрая нарезка"):
            with gr.Row():
                with gr.Column(scale=1):
                    dl_url_input = gr.Textbox(
                        label="Ссылка на видео (YouTube / VK / Rutube)",
                        placeholder="https://www.youtube.com/watch?v=...",
                    )
                    dl_mode = gr.Radio(
                        choices=[
                            ("Скачать видео целиком", "full"),
                            ("Скачать конкретный отрезок (по таймкодам)", "cut"),
                        ],
                        value="full",
                        label="Режим работы",
                    )
                    with gr.Row(visible=False) as time_row:
                        dl_start = gr.Textbox(
                            label="Начало отрезка (например: 01:10 или 70)",
                            value="01:10",
                        )
                        dl_end = gr.Textbox(
                            label="Конец отрезка (например: 02:00 или 120)",
                            value="02:00",
                        )
                    with gr.Row():
                        dl_out_path = gr.Textbox(
                            label="Куда сохранить результат",
                            value=get_default_desktop_path("downloaded_cut.mp4"),
                            scale=4,
                        )
                        dl_browse_btn = gr.Button(
                            "📁 Обзор", scale=1, elem_classes=["browse-btn"]
                        )

                    dl_browse_btn.click(
                        fn=lambda cur: open_folder_dialog(cur, "downloaded_cut.mp4"),
                        inputs=[dl_out_path],
                        outputs=[dl_out_path],
                    )

                    dl_btn = gr.Button("⚡ Скачать", variant="primary")

                with gr.Column(scale=1):
                    dl_result_video = gr.Video(label="Результат")
                    dl_status = gr.Textbox(label="Статус", interactive=False)

            def switch_dl_mode(mode_val):
                return gr.update(visible=(mode_val == "cut"))

            dl_mode.change(switch_dl_mode, inputs=[dl_mode], outputs=time_row)

            dl_btn.click(
                fn=download_or_cut_stream,
                inputs=[dl_url_input, dl_mode, dl_start, dl_end, dl_out_path],
                outputs=[dl_result_video, dl_status],
            )

        # 2. ВКЛАДКА: ПРЕОБРАЗОВАНИЕ 16:9 В 9:16
        with gr.TabItem("🔄 Умное преобразование видео с 16:9 в 9:16"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML("<div class='styled-label-badge'>Загрузите видео формата 16:9</div>")
                    conv_url_input = gr.Textbox(
                        label="Ссылка на видео (YouTube / VK / Rutube)",
                        placeholder="https://www.youtube.com/watch?v=...",
                    )
                    conv_file_input = gr.Video(label="Или загрузите файл с компьютера")

                    with gr.Row():
                        conv_out_path = gr.Textbox(
                            label="Куда сохранить готовое видео",
                            value=get_default_desktop_path("converted_9_16.mp4"),
                            scale=4,
                        )
                        conv_browse_btn = gr.Button(
                            "📁 Обзор", scale=1, elem_classes=["browse-btn"]
                        )

                    conv_browse_btn.click(
                        fn=lambda cur: open_folder_dialog(cur, "converted_9_16.mp4"),
                        inputs=[conv_out_path],
                        outputs=[conv_out_path],
                    )

                    conv_crop_mode = gr.Radio(
                        choices=[
                            ("Полное заполнение (статичный кроп)", "full"),
                            ("Заблюренное (с полосами)", "blur"),
                            ("Умный автокроп (слежение за лицом)", "autotrack"),
                        ],
                        value="autotrack",
                        label="Вид кадрирования",
                    )

                    conv_subtitles_check = gr.Checkbox(
                        value=True, label="Наложить караоке-субтитры"
                    )
                    conv_start_btn = gr.Button("🚀 Сгенерировать ролик", variant="primary")

                with gr.Column(scale=1):
                    conv_result_video = gr.Video(label="Готовый результат")
                    conv_status_output = gr.Textbox(label="Статус", interactive=False)

            conv_start_btn.click(
                fn=convert_16_9_to_9_16,
                inputs=[
                    conv_url_input,
                    conv_file_input,
                    conv_out_path,
                    conv_crop_mode,
                    conv_subtitles_check,
                ],
                outputs=[conv_result_video, conv_status_output],
            )

        # 3. ВКЛАДКА: НАРЕЗКА SHORTS
        with gr.TabItem("🤖 ИИ нарезка Shorts видео"):
            with gr.Row():
                with gr.Column(scale=1):
                    url_input = gr.Textbox(
                        label="Ссылка на видео (YouTube / VK / Rutube)",
                        placeholder="https://vkvideo.ru/video-...",
                    )
                    file_input = gr.Video(label="Или загрузите файл с компьютера")

                    with gr.Row():
                        out_path_input = gr.Textbox(
                            label="Куда сохранить готовое видео",
                            value=get_default_desktop_path("final_clip.mp4"),
                            scale=4,
                        )
                        ai_browse_btn = gr.Button(
                            "📁 Обзор", scale=1, elem_classes=["browse-btn"]
                        )

                    ai_browse_btn.click(
                        fn=lambda cur: open_folder_dialog(cur, "final_clip.mp4"),
                        inputs=[out_path_input],
                        outputs=[out_path_input],
                    )

                    with gr.Row():
                        with gr.Column(scale=1, min_width=110):
                            gr.HTML(
                                "<div class='model-badge-container'>"
                                "<div class='styled-label-badge'>ИИ модели</div>"
                                "</div>"
                            )
                        with gr.Column(scale=4):
                            model_dropdown = gr.Dropdown(
                                choices=LLM_CHOICES,
                                value=DEFAULT_LLM_MODEL,
                                show_label=False,
                            )

                    gr.HTML("<div class='styled-label-badge'>Длительность ролика</div>")
                    with gr.Row():
                        min_sec = gr.Slider(
                            minimum=20,
                            maximum=180,
                            value=20,
                            step=1,
                            label="Мин. секунд",
                        )
                        max_sec = gr.Slider(
                            minimum=20,
                            maximum=180,
                            value=30,
                            step=1,
                            label="Макс. секунд",
                        )

                    crop_mode = gr.Radio(
                        choices=[
                            ("Полное заполнение (статичный кроп)", "full"),
                            ("Заблюренное (с полосами)", "blur"),
                            ("Умный автокроп (слежение за лицом)", "autotrack"),
                        ],
                        value="autotrack",
                        label="Вид кадрирования",
                    )

                    with gr.Row():
                        subtitles_check = gr.Checkbox(
                            value=True,
                            label="Наложить караоке-субтитры",
                        )
                        uniqualize_check = gr.Checkbox(
                            value=True,
                            label="Уникализировать видео (защита от теневых банов)",
                        )

                    start_btn = gr.Button("🚀 Сгенерировать ролик", variant="primary")

                with gr.Column(scale=1):
                    result_video = gr.Video(label="Готовый результат")
                    status_output = gr.Textbox(label="Статус", interactive=False)

            start_btn.click(
                fn=process_video_pipeline,
                inputs=[
                    url_input,
                    file_input,
                    out_path_input,
                    model_dropdown,
                    crop_mode,
                    subtitles_check,
                    min_sec,
                    max_sec,
                    uniqualize_check,
                ],
                outputs=[result_video, status_output],
            )

if __name__ == "__main__":
    allowed_dirs = [get_default_desktop_dir()]
    for drive in ["C:\\", "D:\\", "E:\\"]:
        if os.path.exists(drive):
            allowed_dirs.append(drive)

    demo.launch(inbrowser=True, allowed_paths=allowed_dirs)