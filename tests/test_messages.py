from typing import Dict

import pytest
from eth_utils import is_same_address

from raiden_libs.utils import sign_data, encode_hex, private_key_to_address
from raiden_libs.messages import (
    BalanceProof,
    Message,
    FeeInfo,
    MonitorRequest,
    PathsRequest,
    PathsReply,
)
from raiden_libs.exceptions import MessageTypeError
from raiden_libs.types import Address, ChannelIdentifier


def test_serialize_deserialize(get_random_bp, get_random_privkey):
    bp = get_random_bp()
    privkey = get_random_privkey()
    bp.signature = encode_hex(
        sign_data(
            privkey,
            bp.serialize_bin(),
        ),
    )
    serialized_message = bp.serialize_full()

    deserialized_message = Message.deserialize(serialized_message)
    assert isinstance(deserialized_message, BalanceProof)


def test_balance_proof_address_setter(get_random_bp):
    # test set of checksummed addrs
    bp = get_random_bp()

    # set of an invalid address should raise ValueError
    with pytest.raises(ValueError):
        bp.token_network_address = 123456789
    with pytest.raises(ValueError):
        bp.token_network_address = '0x11e14d102DA61F1a5cA36cfa96C3B831332357b4'


def test_balance_proof():
    # test balance proof with computed balance hash
    balance_proof = BalanceProof(
        channel_identifier=ChannelIdentifier(
            '0x3131313131313131313131313131313131313131313131313131313131313131',
        ),
        token_network_address=Address('0x82dd0e0eA3E84D00Cc119c46Ee22060939E5D1FC'),
        nonce=1,
        chain_id=321,
        transferred_amount=5,
        locksroot='0x%064x' % 5,
        additional_hash='0x%064x' % 0,
    )
    serialized = balance_proof.serialize_data()

    assert serialized['channel_identifier'] == balance_proof.channel_identifier
    assert is_same_address(
        serialized['token_network_address'],
        balance_proof.token_network_address,
    )
    assert serialized['nonce'] == balance_proof.nonce
    assert serialized['chain_id'] == balance_proof.chain_id
    assert serialized['additional_hash'] == balance_proof.additional_hash
    assert serialized['balance_hash'] == balance_proof.balance_hash

    assert serialized['locksroot'] == balance_proof.locksroot
    assert serialized['transferred_amount'] == balance_proof.transferred_amount
    assert serialized['locked_amount'] == balance_proof.locked_amount

    # test balance proof with balance hash set from constructor
    balance_proof = BalanceProof(
        channel_identifier=ChannelIdentifier(
            '0x3131313131313131313131313131313131313131313131313131313131313131',
        ),
        token_network_address=Address('0x82dd0e0eA3E84D00Cc119c46Ee22060939E5D1FC'),
        nonce=1,
        chain_id=321,
        balance_hash='0x%064x' % 5,
        locked_amount=0,
        additional_hash='0x%064x' % 0,
    )
    serialized = balance_proof.serialize_data()

    with pytest.raises(KeyError):
        serialized['transferred_amount']

    assert serialized['channel_identifier'] == balance_proof.channel_identifier
    assert is_same_address(
        serialized['token_network_address'],
        balance_proof.token_network_address,
    )
    assert serialized['nonce'] == balance_proof.nonce
    assert serialized['chain_id'] == balance_proof.chain_id
    assert serialized['additional_hash'] == balance_proof.additional_hash
    assert serialized['balance_hash'] == balance_proof.balance_hash


def test_fee_info():
    message: Dict = dict(
        message_type='FeeInfo',
        token_network_address='0x82dd0e0eA3E84D00Cc119c46Ee22060939E5D1FC',
        chain_id=1,
        channel_identifier='0x3131313131313131313131313131313131313131313131313131313131313131',
        nonce=1,
        relative_fee=10000,
        signature='signature',
    )
    assert message == Message.deserialize(message).serialize_data()
    message['message_type'] = 'FeeInfo'
    assert isinstance(Message.deserialize(message), FeeInfo)


def test_paths_request():
    message: Dict = dict(
        message_type='PathsRequest',
        token_network_address='0x82dd0e0eA3E84D00Cc119c46Ee22060939E5D1FC',
        source_address='0x82dd0e0eA3E84D00Cc119c46Ee22060939E5D1FC',
        target_address='0x82dd0e0eA3E84D00Cc119c46Ee22060939E5D1FC',
        value=1000,
        num_paths=1,
        chain_id=1,
        nonce=1,
        signature='signature',
    )

    assert message == Message.deserialize(message).serialize_data()
    message['message_type'] = 'PathsRequest'
    assert isinstance(Message.deserialize(message), PathsRequest)


def test_paths_reply():
    message: Dict = dict(
        message_type='PathsReply',
        token_network_address='0x82dd0e0eA3E84D00Cc119c46Ee22060939E5D1FC',
        target_address='0x82dd0e0eA3E84D00Cc119c46Ee22060939E5D1FC',
        value=1000,
        chain_id=1,
        nonce=1,
        paths_and_fees=[{
            'estimated_fee': 10000,
            'paths': [[
                '0x82dd0e0eA3E84D00Cc119c46Ee220609',
                '0xA3E84D00Cc119c46Ee22060939E5D1FC',
            ]],
        }],
        signature='signature',
    )

    assert message == Message.deserialize(message).serialize_data()
    message['message_type'] = 'PathsReply'
    assert isinstance(Message.deserialize(message), PathsReply)


def test_deserialize_with_required_type():
    message: Dict = dict(
        message_type='FeeInfo',
        token_network_address='0x82dd0e0eA3E84D00Cc119c46Ee22060939E5D1FC',
        chain_id=1,
        channel_identifier='0x3131313131313131313131313131313131313131313131313131313131313131',
        nonce=1,
        relative_fee=1000,
        signature='signature',
    )

    deserialized_message = Message.deserialize(message, FeeInfo)
    assert isinstance(deserialized_message, FeeInfo)

    # during deserialization the `message_type` is removed, add it back
    message['message_type'] = 'FeeInfo'
    with pytest.raises(MessageTypeError):
        Message.deserialize(message, BalanceProof)


def test_monitor_request(get_random_bp, get_random_privkey, get_random_address):
    balance_proof = get_random_bp()
    client_privkey = get_random_privkey()
    reward_sender_privkey = get_random_privkey()
    balance_proof.signature = encode_hex(sign_data(client_privkey, balance_proof.serialize_bin()))
    monitor_request = MonitorRequest(
        balance_proof,
        non_closing_signature=balance_proof.signature,
        reward_proof_signature='',
        reward_amount=1,
        monitor_address=get_random_address(),
    )
    monitor_request.reward_proof_signature = encode_hex(
        sign_data(
            reward_sender_privkey,
            monitor_request.serialize_reward_proof(),
        ),
    )

    serialized = monitor_request.serialize_data()
    monitor_request_verify = MonitorRequest.deserialize(serialized)
    balance_proof_verify = monitor_request_verify.balance_proof
    assert is_same_address(monitor_request_verify.monitor_address, monitor_request.monitor_address)
    assert is_same_address(
        monitor_request_verify.reward_proof_signer,
        monitor_request.reward_proof_signer,
    )
    assert is_same_address(
        monitor_request.reward_proof_signer,
        private_key_to_address(reward_sender_privkey),
    )
    assert monitor_request_verify.non_closing_signature == monitor_request.non_closing_signature
    assert monitor_request_verify.reward_amount == monitor_request.reward_amount
    assert is_same_address(
        balance_proof_verify.token_network_address,
        balance_proof.token_network_address,
    )
    assert balance_proof_verify.chain_id == balance_proof.chain_id
    assert balance_proof_verify.channel_identifier == balance_proof.channel_identifier
    assert balance_proof_verify.nonce == balance_proof.nonce
