from PIL import Image
import argparse

def text_to_bits(text):
    """
    Преобразует текст в битовую строку через кодировку UTF-8.

    Args:
        text (str): Входной текст.

    Returns:
        list: Список битов (0 или 1).
    """
    # Удаляем возможные CRLF, BOM, пробелы и другие управляющие символы
    text = ''.join(c for c in text if c.isprintable() or c == ' ')
    # Кодируем текст в байты UTF-8
    bytes_text = text.encode('utf-8')
    bits = []
    for byte in bytes_text:
        bin_byte = bin(byte)[2:].zfill(8)
        bits.extend([int(b) for b in bin_byte])
    return bits

def bits_to_text(bits):
    """
    Преобразует битовую строку в текст через декодировку UTF-8.

    Args:
        bits (list): Список битов (0 или 1).

    Returns:
        str: Декодированный текст.
    """
    bytes_list = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8:
            break
        byte_value = int(''.join(str(b) for b in byte), 2)
        bytes_list.append(byte_value)
    return bytes(bytes_list).decode('utf-8', errors='ignore')

def int_to_bits(number, length=32):
    """
    Преобразует целое число в битовую строку фиксированной длины.

    Args:
        number (int): Число для преобразования.
        length (int): Длина битовой строки (по умолчанию 32).

    Returns:
        list: Список битов.
    """
    return [int(b) for b in bin(number)[2:].zfill(length)]

def bits_to_int(bits):
    """
    Преобразует битовую строку в целое число.

    Args:
        bits (list): Список битов.

    Returns:
        int: Число.
    """
    return int(''.join(str(b) for b in bits), 2)

def embed_message(image_path, message, output_path):
    """
    Встраивает сообщение в изображение методом LSB.

    Args:
        image_path (str): Путь к исходному изображению.
        message (str): Сообщение для встраивания.
        output_path (str): Путь для сохранения стегоконтейнера.

    Raises:
        ValueError: Если изображение слишком мало или формат не поддерживается.
    """
    try:
        img = Image.open(image_path)
        if not image_path.lower().endswith('.png'):
            img = img.convert('RGB')
            temp_path = 'temp.png'
            img.save(temp_path, 'PNG')
            img = Image.open(temp_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        pixels = img.load()
        width, height = img.size

        # Преобразуем сообщение в биты и добавляем длину
        message_bits = text_to_bits(message)
        length_bits = int_to_bits(len(message_bits))
        all_bits = length_bits + message_bits

        # Проверяем, достаточно ли пикселей
        required_pixels = len(all_bits) // 3 + (1 if len(all_bits) % 3 else 0)
        if required_pixels > width * height:
            raise ValueError(f"Изображение слишком мало для встраивания {len(all_bits)} бит")

        bit_index = 0
        for y in range(height):
            for x in range(width):
                if bit_index >= len(all_bits):
                    break
                r, g, b = pixels[x, y]
                if bit_index < len(all_bits):
                    r = (r & ~1) | all_bits[bit_index]
                    bit_index += 1
                if bit_index < len(all_bits):
                    g = (g & ~1) | all_bits[bit_index]
                    bit_index += 1
                if bit_index < len(all_bits):
                    b = (b & ~1) | all_bits[bit_index]
                    bit_index += 1
                pixels[x, y] = (r, g, b)
            if bit_index >= len(all_bits):
                break

        img.save(output_path, 'PNG')
        print(f"Сообщение успешно встроено в {output_path}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Файл {image_path} не найден")
    except Exception as e:
        raise ValueError(f"Ошибка при обработке изображения: {str(e)}")

def extract_message(image_path):
    """
    Извлекает сообщение из стегоконтейнера.

    Args:
        image_path (str): Путь к изображению-стегоконтейнеру.

    Returns:
        str: Извлечённое сообщение.

    Raises:
        ValueError: Если изображение не содержит валидного сообщения.
    """
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    pixels = img.load()
    width, height = img.size

    # Собираем все биты последовательно
    all_bits = []
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            all_bits.append(r & 1)
            all_bits.append(g & 1)
            all_bits.append(b & 1)
            if len(all_bits) >= 32 + width * height * 3:
                break
        if len(all_bits) >= 32 + width * height * 3:
            break

    # Извлекаем длину сообщения (первые 32 бита)
    length_bits = all_bits[:32]
    message_length = bits_to_int(length_bits)
    if message_length > width * height * 3:
        raise ValueError("Недопустимая длина сообщения или сообщение отсутствует")

    # Извлекаем биты сообщения (с 33-го бита)
    message_bits = all_bits[32:32 + message_length]
    return bits_to_text(message_bits)

def main():
    """Точка входа для программы."""
    parser = argparse.ArgumentParser(description="Программа для LSB-стеганографии")
    parser.add_argument('--embed', action='store_true', help='Встроить сообщение')
    parser.add_argument('--extract', action='store_true', help='Извлечь сообщение')
    parser.add_argument('--image', type=str, required=True, help='Путь к изображению')
    parser.add_argument('--message', type=str, help='Сообщение для встраивания')
    parser.add_argument('--output', type=str, default='output.png', help='Путь для сохранения стегоконтейнера')
    
    args = parser.parse_args()

    try:
        if args.embed:
            if not args.message:
                raise ValueError("Для встраивания требуется указать сообщение (--message)")
            embed_message(args.image, args.message, args.output)
        elif args.extract:
            message = extract_message(args.image)
            print(f"Извлечённое сообщение: {message}")
        else:
            raise ValueError("Укажите режим: --embed или --extract")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()