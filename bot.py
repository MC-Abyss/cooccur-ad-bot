import os
import traceback
from skimage import io
from skimage.color import rgb2gray
import matplotlib.pyplot as plt
import numpy as np
from telegram import Bot, Update
from telegram.ext import Updater, MessageHandler, Filters
from cooccur2D import cooccur2D

#working dir
DATA_DIR = 'tmp_data'


def message_handler(update: Update, context):
    try:
        user = update.effective_user
        name = user.first_name if user else 'Anonymous'

        chat_id = update.effective_message.chat_id
        out_text, local_file_path = get_image_from_message(context.bot, update)

        if not local_file_path:
            reply_text = f'Hi, {name}\n'
            reply_text += 'I can plot histogram of angles at adjacent pixels. Please send me an image.'
            context.bot.send_message(chat_id=chat_id, text=reply_text)
        else:
            context.bot.send_message(chat_id=chat_id, text='Processing...')
            img = rgb2gray(io.imread(local_file_path)).astype(float)
            result_path = os.path.join(DATA_DIR, 'hist.png')
            if os.path.exists(result_path):
                plt.clf()
                os.remove(result_path)
            intensity_bins = 1
            angle_bins = 9
            distance = 1
            comatrix = cooccur2D(img, i_bins=intensity_bins, a_bins=angle_bins, dists=(distance,), mask=None)
            if len(comatrix.shape) == 2:
                plt.imshow(comatrix, cmap='jet')
            elif len(comatrix.shape) == 1:
                plt.bar(np.arange(comatrix.shape[0]), comatrix / np.max(comatrix))
            plt.savefig(result_path)
            out_text = f'AD matrix with D=1 (histogram of angles at adjacent pixels):'
            print(out_text)
            context.bot.send_message(chat_id=chat_id, text=out_text)
            context.bot.send_photo(chat_id=chat_id, photo=open(result_path, 'rb'))
    except:
        chat_id = update.effective_message.chat_id
        err_txt = traceback.format_exc()
        reply_text = 'An error occurred -.-\n\n' + err_txt
        context.bot.send_message(chat_id=chat_id, text=reply_text)


def get_image_from_message(bot: Bot, update: Update):
    document = update.effective_message.document
    photo = update.effective_message.photo
    out_text, file_id = None, None

    if document:
        if not document.__class__ == list:
            document = [document]

        document = [doc for doc in document if doc.mime_type.startswith('image')]

        if document:
            out_text = 'Found image as document'
            file_id = document[0].file_id

    if photo:
        if not photo.__class__ == list:
            photo = [photo]

        num_pix_photo = [(p.height * p.width, p) for p in photo]
        ph = sorted(num_pix_photo, reverse=True)[0][1]
        w, h = ph.width, ph.height

        out_text = f'Found image as photo of resolution {w}x{h}'
        file_id = ph.file_id

    if file_id:
        file = bot.getFile(file_id)
        _, ext = os.path.splitext(file.file_path)
        local_file_path = os.path.join(DATA_DIR, 'input' + ext)
        os.makedirs(DATA_DIR, exist_ok=True)
        file.download(custom_path=local_file_path)

        return out_text, local_file_path

    return None, None


def main():

    tg_token = os.getenv("TOKEN")

    bot = Bot(token=tg_token)
    updater = Updater(bot=bot)

    handler = MessageHandler(Filters.all, message_handler)
    updater.dispatcher.add_handler(handler)
    PORT = int(os.environ.get("PORT", "8443"))  ###Избегаем ошибки Heroku R10
    HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=tg_token)
    print("Starting...")
    updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, tg_token))

if __name__ == '__main__':
    main()
