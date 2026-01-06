import unittest
from encoding_fix import convert_encs
import mutagen.id3 as ID3


class MyTestCase(unittest.TestCase):
    def test_convert_album_success(self):
        subj = ID3.TALB(encoding=ID3.Encoding.LATIN1, text="Äîæäèê, äîæäèê, ïåðåñòàíü")
        res = convert_encs(subj)
        self.assertEqual("Дождик, дождик, перестань", res)

    def test_convert_artist_success(self):
        subj = ID3.TPE1(
            encoding=ID3.Encoding.LATIN1,
            text=['Âëàä Êîïï, DJ Ìèõàèë Ãàáîâè÷, DJ Àíäðåé Addison'],
        )
        res = convert_encs(subj)
        self.assertEqual("Влад Копп, DJ Михаил Габович, DJ Андрей Addison", res)

    def test_convert_title_success(self):
        subj = ID3.TIT2(
            encoding=ID3.Encoding.LATIN1,
            text=['Õàðëàí Ýëëèñîí - "Ïîêàéñÿ, Àðëåêèí! - ñêàçàë Òèêòàêùèê"'],
        )
        res = convert_encs(subj)
        self.assertEqual(
            "Харлан Эллисон - \"Покайся, Арлекин! - сказал Тиктакщик\"", res
        )

    def test_convert_album_fail_found_utf(self):
        subj = ID3.TALB(ID3.Encoding.UTF8, "Äîæäèê, äîæäèê, ïåðåñòàíü")
        with self.assertRaises(EncodingWarning):
            convert_encs(subj)

    def test_convert_album_fail_no_text(self):
        subj = ID3.TALB(ID3.Encoding.LATIN1)
        with self.assertRaises(IndexError):
            convert_encs(subj)

    def test_convert_album_utf16(self):
        subj = ID3.TALB(ID3.Encoding.UTF16, "•модель для сборки•")
        with self.assertRaises(EncodingWarning):
            convert_encs(subj)

    def test_convert_cp1251(self):
        subj = ID3.TIT2(
            encoding=ID3.Encoding.LATIN1, text=['Ïåñåíêà Ëüâåíêà è ×åðåïàõè']
        )
        res = convert_encs(subj)
        self.assertEqual("Песенка Львенка и Черепахи", res)


if __name__ == '__main__':
    unittest.main()
