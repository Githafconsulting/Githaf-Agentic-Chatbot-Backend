"""
Unit tests for geolocation utility
"""
import pytest
from app.utils.geolocation import anonymize_ip


@pytest.mark.unit
def test_anonymize_ipv4():
    """Test IPv4 anonymization"""
    ip = "192.168.1.100"
    result = anonymize_ip(ip)
    assert result == "192.168.1.0"


@pytest.mark.unit
def test_anonymize_ipv6():
    """Test IPv6 anonymization"""
    ip = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    result = anonymize_ip(ip)
    assert result == "2001:0db8:85a3:0000:0000:8a2e:0:0"


@pytest.mark.unit
def test_anonymize_localhost():
    """Test localhost anonymization"""
    ip = "127.0.0.1"
    result = anonymize_ip(ip)
    assert result == "127.0.0.0"
