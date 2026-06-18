import os
import re
import hashlib
from collections import defaultdict

REPORT_FILE = "duplicates_report.txt"


# ==========================================================
# Нормализация имен
# ==========================================================

def normalize_name(filename):
    name, ext = os.path.splitext(filename)

    name = name.lower()
    name = re.sub(r"\s+", " ", name)
    name = name.strip()

    return name + ext.lower()


def normalize_brackets(filename):
    name, ext = os.path.splitext(filename)

    name = name.lower()
    name = re.sub(r"\s+", " ", name)
    name = name.strip()

    name = re.sub(r"\s*\(\d+\)$", "", name)

    return name + ext.lower()


# ==========================================================
# Сканирование файлов
# ==========================================================

def scan_files(root_dir, extension):

    files = []

    extension = extension.lower().lstrip(".")

    for root, dirs, filenames in os.walk(root_dir):

        for filename in filenames:

            if extension != "*":
                if not filename.lower().endswith("." + extension):
                    continue

            files.append(
                os.path.join(root, filename)
            )

    return files


# ==========================================================
# Формирование групп
# ==========================================================

def build_groups(files, key_func):

    groups = defaultdict(list)

    for path in files:

        try:
            key = key_func(path)
            groups[key].append(path)

        except:
            pass

    result = []

    for group in groups.values():

        if len(group) > 1:
            result.append(group)

    return result


# ==========================================================
# Алгоритмы
# ==========================================================

def pass_name(files):

    return build_groups(
        files,
        lambda p: normalize_name(
            os.path.basename(p)
        )
    )


def pass_brackets(files):

    return build_groups(
        files,
        lambda p: normalize_brackets(
            os.path.basename(p)
        )
    )


def pass_size(files):

    return build_groups(
        files,
        lambda p: os.path.getsize(p)
    )


# ==========================================================
# SHA256
# ==========================================================

def file_hash(path):

    sha = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            block = f.read(1024 * 1024)

            if not block:
                break

            sha.update(block)

    return sha.hexdigest()


def pass_hash(files):

    groups = defaultdict(list)

    total = len(files)

    for i, path in enumerate(files, start=1):

        print(
            f"\rХэширование {i}/{total}",
            end=""
        )

        try:

            h = file_hash(path)

            groups[h].append(path)

        except:
            pass

    print()

    result = []

    for group in groups.values():

        if len(group) > 1:
            result.append(group)

    return result


# ==========================================================
# Сужение кандидатов
# ==========================================================

def flatten_groups(groups):

    result = []

    for group in groups:
        result.extend(group)

    return result


# ==========================================================
# Преобразование в структуру дублей
# ==========================================================

def make_duplicates(groups):

    duplicates = []

    for group in groups:

        duplicates.append(
            {
                "original": group[0],
                "duplicates": group[1:]
            }
        )

    return duplicates


# ==========================================================
# Статистика
# ==========================================================

def print_stats(groups):

    group_count = len(groups)

    dup_count = 0

    for group in groups:
        dup_count += len(group) - 1

    print()
    print(f"Групп дублей : {group_count}")
    print(f"Дублей       : {dup_count}")
    print(f"Файлов всего : {sum(len(g) for g in groups)}")
    print()


# ==========================================================
# Просмотр
# ==========================================================

def show_duplicates(duplicates):

    if not duplicates:

        print("\nНичего не найдено.\n")
        return

    for i, group in enumerate(duplicates, start=1):

        print()
        print("=" * 80)
        print(f"ГРУППА #{i}")
        print()

        print("ОРИГИНАЛ:")
        print(group["original"])

        print()
        print("ДУБЛИ:")

        for dup in group["duplicates"]:
            print("  " + dup)

        print()


# ==========================================================
# Отчет
# ==========================================================

def save_report(duplicates):

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as report:

        for i, group in enumerate(duplicates, start=1):

            report.write("=" * 80 + "\n")
            report.write(f"ГРУППА #{i}\n\n")

            report.write("ОРИГИНАЛ:\n")
            report.write(group["original"] + "\n\n")

            report.write("ДУБЛИ:\n")

            for dup in group["duplicates"]:
                report.write(dup + "\n")

            report.write("\n")

    print(f"\nОтчет сохранен: {REPORT_FILE}\n")


# ==========================================================
# Размер освобождаемого места
# ==========================================================

def calculate_space(duplicates):

    count = 0
    total_size = 0

    for group in duplicates:

        for dup in group["duplicates"]:

            try:

                total_size += os.path.getsize(dup)
                count += 1

            except:
                pass

    return count, total_size


# ==========================================================
# Удаление
# ==========================================================

def delete_duplicates(duplicates):

    count, size = calculate_space(
        duplicates
    )

    print()
    print(f"Будет удалено файлов: {count}")
    print(
        f"Освободится: "
        f"{size / 1024**3:.2f} ГБ"
    )

    answer = input(
        "\nУдалить? (y/n): "
    ).lower()

    if answer != "y":
        return

    deleted = 0
    errors = 0

    for group in duplicates:

        for dup in group["duplicates"]:

            try:

                os.remove(dup)
                deleted += 1

            except:

                errors += 1

    print()
    print(f"Удалено : {deleted}")
    print(f"Ошибок  : {errors}")
    print()


# ==========================================================
# Главное меню
# ==========================================================

def main():

    print("ПОИСК ДУБЛИКАТОВ\n")

    folder = input(
        "Папка для сканирования: "
    ).strip()

    if not os.path.isdir(folder):

        print("Папка не найдена.")
        return

    extension = input(
        "Расширение (mp3/mp4/*): "
    ).strip()

    print("\nСканирование...")

    all_files = scan_files(
        folder,
        extension
    )

    print(
        f"Найдено файлов: "
        f"{len(all_files)}"
    )

    candidates = all_files[:]
    current_groups = []
    used_passes = set()

    while True:

        print()
        print("1 - По имени")
        print("2 - По имени + (число)")
        print("3 - По размеру")
        print("4 - По SHA256")
        print()
        print("5 - Показать группы")
        print("6 - Сохранить отчет")
        print("7 - Удалить дубли")
        print("0 - Выход")

        choice = input("\n> ").strip()

        if choice == "0":
            break

        elif choice == "1":

            if 1 in used_passes:
                print("Проход уже выполнен.")
                continue

            current_groups = pass_name(
                candidates
            )

            candidates = flatten_groups(
                current_groups
            )

            used_passes.add(1)

            print_stats(current_groups)

        elif choice == "2":

            if 2 in used_passes:
                print("Проход уже выполнен.")
                continue

            current_groups = pass_brackets(
                candidates
            )

            candidates = flatten_groups(
                current_groups
            )

            used_passes.add(2)

            print_stats(current_groups)

        elif choice == "3":

            if 3 in used_passes:
                print("Проход уже выполнен.")
                continue

            current_groups = pass_size(
                candidates
            )

            candidates = flatten_groups(
                current_groups
            )

            used_passes.add(3)

            print_stats(current_groups)

        elif choice == "4":

            if 4 in used_passes:
                print("Проход уже выполнен.")
                continue

            current_groups = pass_hash(
                candidates
            )

            candidates = flatten_groups(
                current_groups
            )

            used_passes.add(4)

            print_stats(current_groups)

        elif choice == "5":

            duplicates = make_duplicates(
                current_groups
            )

            show_duplicates(
                duplicates
            )

        elif choice == "6":

            duplicates = make_duplicates(
                current_groups
            )

            save_report(
                duplicates
            )

        elif choice == "7":

            duplicates = make_duplicates(
                current_groups
            )

            delete_duplicates(
                duplicates
            )

            break


if __name__ == "__main__":
    main()