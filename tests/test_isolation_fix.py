"""Minimal test to demonstrate and validate the test isolation fix."""
import pytest
import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Set testing environment
os.environ["TESTING"] = "1"

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Create test models
Base = declarative_base()

class TestUser(Base):
    __tablename__ = "test_users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    name = Column(String)
    strategies = relationship("TestStrategy", back_populates="user")

class TestStrategy(Base):
    __tablename__ = "test_strategies"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("test_users.id"))
    name = Column(String)
    user = relationship("TestUser", back_populates="strategies")


class TestIsolationFix:
    """Test class to validate database isolation between tests."""
    
    @pytest.fixture(scope="function")
    def isolated_db(self):
        """Create completely isolated in-memory database for each test."""
        # Use a unique in-memory database for each test
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=engine)
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        yield session
        
        session.close()
        engine.dispose()
    
    def test_isolation_1_create_user_and_strategy(self, isolated_db):
        """Test 1: Create user and strategy, verify counts."""
        session = isolated_db
        
        # Initially should be empty
        users = session.query(TestUser).all()
        strategies = session.query(TestStrategy).all()
        assert len(users) == 0, f"Expected 0 users initially, found {len(users)}"
        assert len(strategies) == 0, f"Expected 0 strategies initially, found {len(strategies)}"
        
        # Create user
        user = TestUser(email="test1@example.com", name="Test User 1")
        session.add(user)
        session.commit()
        
        # Create strategy
        strategy = TestStrategy(user_id=user.id, name="Strategy 1")
        session.add(strategy)
        session.commit()
        
        # Verify counts
        users = session.query(TestUser).all()
        strategies = session.query(TestStrategy).all()
        assert len(users) == 1, f"Expected 1 user after creation, found {len(users)}"
        assert len(strategies) == 1, f"Expected 1 strategy after creation, found {len(strategies)}"
        
        print(f"Test 1: Created {len(users)} user(s) and {len(strategies)} strategy(ies)")
    
    def test_isolation_2_fresh_database_check(self, isolated_db):
        """Test 2: Should start with completely fresh database."""
        session = isolated_db
        
        # Should be completely empty - no data from test 1
        users = session.query(TestUser).all()
        strategies = session.query(TestStrategy).all()
        assert len(users) == 0, f"Expected 0 users due to isolation, found {len(users)}"
        assert len(strategies) == 0, f"Expected 0 strategies due to isolation, found {len(strategies)}"
        
        # Create different data
        user = TestUser(email="test2@example.com", name="Test User 2")
        session.add(user)
        session.commit()
        
        strategy1 = TestStrategy(user_id=user.id, name="Strategy A")
        strategy2 = TestStrategy(user_id=user.id, name="Strategy B")
        session.add_all([strategy1, strategy2])
        session.commit()
        
        # Verify counts
        users = session.query(TestUser).all()
        strategies = session.query(TestStrategy).all()
        assert len(users) == 1, f"Expected 1 user in test 2, found {len(users)}"
        assert len(strategies) == 2, f"Expected 2 strategies in test 2, found {len(strategies)}"
        
        print(f"Test 2: Created {len(users)} user(s) and {len(strategies)} strategy(ies)")
    
    def test_isolation_3_verify_continued_isolation(self, isolated_db):
        """Test 3: Verify isolation continues to work."""
        session = isolated_db
        
        # Again, should be completely empty
        users = session.query(TestUser).all()
        strategies = session.query(TestStrategy).all()
        assert len(users) == 0, f"Expected 0 users due to continued isolation, found {len(users)}"
        assert len(strategies) == 0, f"Expected 0 strategies due to continued isolation, found {len(strategies)}"
        
        print(f"Test 3: Confirmed isolation - found {len(users)} user(s) and {len(strategies)} strategy(ies)")
    
    def test_isolation_4_multiple_operations(self, isolated_db):
        """Test 4: Multiple operations within single test."""
        session = isolated_db
        
        # Start empty
        assert len(session.query(TestUser).all()) == 0
        assert len(session.query(TestStrategy).all()) == 0
        
        # Create multiple users and strategies
        for i in range(3):
            user = TestUser(email=f"user{i}@example.com", name=f"User {i}")
            session.add(user)
            session.commit()
            
            for j in range(2):
                strategy = TestStrategy(user_id=user.id, name=f"Strategy {i}-{j}")
                session.add(strategy)
            
        session.commit()
        
        # Verify final counts
        users = session.query(TestUser).all()
        strategies = session.query(TestStrategy).all()
        assert len(users) == 3, f"Expected 3 users, found {len(users)}"
        assert len(strategies) == 6, f"Expected 6 strategies, found {len(strategies)}"
        
        print(f"Test 4: Created {len(users)} user(s) and {len(strategies)} strategy(ies)")
    
    def test_isolation_5_final_verification(self, isolated_db):
        """Test 5: Final verification that isolation works."""
        session = isolated_db
        
        # Should still be empty
        users = session.query(TestUser).all()
        strategies = session.query(TestStrategy).all()
        assert len(users) == 0, f"Expected 0 users in final test, found {len(users)}"
        assert len(strategies) == 0, f"Expected 0 strategies in final test, found {len(strategies)}"
        
        print(f"Test 5: Final verification - found {len(users)} user(s) and {len(strategies)} strategy(ies)")


def test_demonstrate_old_problem():
    """Demonstrate what the old test isolation problem looked like."""
    # This test shows how the old approach would fail
    
    # Simulate the old approach with shared database
    engine = create_engine("sqlite:///shared_test.db", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # First "test" creates data
    session1 = SessionLocal()
    user1 = TestUser(email="shared1@example.com", name="Shared User 1")
    session1.add(user1)
    session1.commit()
    
    strategy1 = TestStrategy(user_id=user1.id, name="Shared Strategy 1")
    session1.add(strategy1)
    session1.commit()
    
    count_after_test1 = len(session1.query(TestStrategy).all())
    session1.close()
    
    # Second "test" sees leftover data
    session2 = SessionLocal()
    existing_strategies = session2.query(TestStrategy).all()
    count_before_test2_creation = len(existing_strategies)
    
    # Second test creates its own strategy
    user2 = TestUser(email="shared2@example.com", name="Shared User 2") 
    session2.add(user2)
    session2.commit()
    
    strategy2 = TestStrategy(user_id=user2.id, name="Shared Strategy 2")
    session2.add(strategy2)
    session2.commit()
    
    count_after_test2 = len(session2.query(TestStrategy).all())
    session2.close()
    
    # Clean up
    engine.dispose()
    import os
    if os.path.exists("shared_test.db"):
        os.remove("shared_test.db")
    
    print(f"Old approach demonstration:")
    print(f"  After test 1: {count_after_test1} strategy(ies)")
    print(f"  Before test 2 creation: {count_before_test2_creation} strategy(ies) (leftover!)")
    print(f"  After test 2: {count_after_test2} strategy(ies)")
    
    # This demonstrates the problem: test 2 saw leftover data from test 1
    assert count_before_test2_creation > 0, "This shows the old isolation problem"
    assert count_after_test2 > 1, "Multiple tests worth of data accumulated"


if __name__ == "__main__":
    # Run a quick demonstration
    print("Running test isolation demonstration...")
    test_demonstrate_old_problem()
    print("✅ Demonstrated the old problem")
    print("\nThe new fixtures in conftest.py solve this by:")
    print("1. Using in-memory SQLite databases")
    print("2. Creating fresh database engine per test") 
    print("3. Using transactions with rollback")
    print("4. Proper session management")
    print("\nRun: pytest tests/test_isolation_fix.py -v to see the new approach working")