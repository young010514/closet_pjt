from django.db import models

from common.models import ActiveModel, TimeStampedModel


class Store(TimeStampedModel, ActiveModel):
    """
    공공데이터에서 수집한 옷가게와
    사업자 회원이 관리하는 가게 정보를 저장한다.
    """

    business_profile = models.ForeignKey(
        "accounts.BusinessProfile",
        on_delete=models.SET_NULL,
        related_name="stores",
        null=True,
        blank=True,
        verbose_name="관리 사업자",
    )

    # 소상공인시장진흥공단 데이터의 상가업소번호
    # 사업자가 직접 등록하는 가게는 값이 없을 수 있다.
    external_store_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="외부 상가업소번호",
    )

    name = models.CharField(
        max_length=200,
        verbose_name="상호명",
    )

    branch_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="지점명",
    )

    category_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="업종 코드",
    )

    category_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="업종명",
    )

    region = models.ForeignKey(
        "regions.Region",
        on_delete=models.PROTECT,
        related_name="stores",
        verbose_name="지역",
    )

    jibun_address = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="지번 주소",
    )

    road_address = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="도로명 주소",
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        verbose_name="경도",
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=7,
        verbose_name="위도",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="전화번호",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="가게 소개",
    )

    opening_hours = models.TextField(
        blank=True,
        default="",
        verbose_name="영업시간",
    )

    website_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="웹사이트 주소",
    )

    view_count = models.PositiveBigIntegerField(
        default=0,
        db_index=True,
        verbose_name="조회수",
    )

    data_source = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="데이터 출처",
    )

    class Meta:
        db_table = "stores"
        verbose_name = "가게"
        verbose_name_plural = "가게"
        ordering = ["name", "id"]

        indexes = [
            models.Index(
                fields=["region", "is_active"],
                name="stores_region_active_idx",
            ),
            models.Index(
                fields=["category_code"],
                name="stores_category_idx",
            ),
            models.Index(
                fields=["name"],
                name="stores_name_idx",
            ),
        ]

    def __str__(self):
        if self.branch_name:
            return f"{self.name} {self.branch_name}"

        return self.name

    @property
    def full_address(self):
        return self.road_address or self.jibun_address

    @property
    def is_claimed(self):
        """사업자 회원에게 연결된 가게인지 확인한다."""
        return self.business_profile_id is not None
