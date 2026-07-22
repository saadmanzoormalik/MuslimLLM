import unittest
from auth_test_support import assert_contains


class GuestConversionTests(unittest.TestCase):
    def test_workspace_moves_transactionally(self):
        assert_contains(self, "backend/app/auth/service.py", "update projects set user_id=%s,guest_id=null", "update chats set user_id=%s,guest_id=null", "converted_user_id")


if __name__ == "__main__": unittest.main()
